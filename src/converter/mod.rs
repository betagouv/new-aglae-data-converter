use indicatif::{ProgressBar, ProgressStyle};
use log::{debug, error, info};
use ndarray::{s, Array3};
use std::{
    collections::HashMap,
    fs::File,
    io::{BufRead, BufReader, Read, Seek, SeekFrom},
    path,
    result::Result,
    sync::mpsc,
    thread,
};

pub mod config;
use config::{Detector, LstConfig};

pub mod models;
use models::{ExpInfo, LSTDataset, MapSize};

mod events;
use events::LstEvent;

mod helpers;
use helpers::{add_data_to_ndarray, format_milliseconds, get_adcnum};

use crate::converter::models::LSTData;

use self::models::ParsingResult;

#[derive(Debug, Clone, Copy)]
struct Position {
    x: u16,
    y: u16,
}

pub fn parse_lst(file_path: &path::Path, config: LstConfig) -> Result<ParsingResult, &'static str> {
    info!("File to parse: {:?}", file_path);
    info!("Config used: {:?}", config);

    let file = File::open(file_path).expect("Error opening file");
    // Get the total size of the file
    let file_size = file.metadata().unwrap().len();

    let mut reader = BufReader::new(file);

    let (map_size, exp_info, timer_reduce) = read_header(&mut reader).unwrap();
    debug!("Map size: {:?}", map_size);
    if let Some(exp_info) = exp_info.clone() {
        debug!("Exp info: {:?}", exp_info);
    }

    let max_x = map_size.get_max_x();
    let max_y = map_size.get_max_y();

    let pb = ProgressBar::new(file_size);
    pb.set_style(
        ProgressStyle::with_template(
            "{spinner:.green}  [{elapsed_precise}] [{wide_bar:.cyan/blue}] {bytes}/{total_bytes}",
        )
        .unwrap()
        .progress_chars("#>-"),
    );

    let (tx, rx) = mpsc::channel();

    let config_thread = config.clone();
    let mut dataset = config_thread.create_big_dataset(max_x, max_y);
    debug!("Dataset created: {:?}", dataset.shape());

    // Launch thread to parse the file
    let handle_dataset = thread::spawn(move || -> Result<(LSTDataset, i32, u32), &str> {
        let mut timer_events: u32 = 0;
        let mut total_events = 0;

        let mut buffer = [0; 4];
        let mut position: Position = Position { x: 0, y: 0 };

        #[allow(unused_assignments)] // False positive (I think)
        let mut binary_value: u32 = 0;

        // Read 4 bytes at a time
        loop {
            if let Err(_err) = reader.read_exact(&mut buffer) {
                break;
            }

            binary_value = u32::from_le_bytes(buffer);
            match LstEvent::inspect(binary_value) {
                Some(LstEvent::Timer) => {
                    timer_events += 1;

                    let current_position = reader.seek(SeekFrom::Current(0)).expect("Couldn't read position");
                    if let Err(err) = tx.send(current_position) {
                        error!("Couldn't send position: {}", err);
                    }
                }
                Some(LstEvent::Adc(has_dummy_word)) => {
                    total_events += 1;

                    if has_dummy_word {
                        // Dummy word was inserted, read 2 bytes
                        if let Err(err) = reader.seek(SeekFrom::Current(2)) {
                            error!("Couldn't seek: {}", err);
                        }
                    }

                    let adcnum = get_adcnum(binary_value);
                    let mut adc_buffer = vec![0; adcnum.len() * 2 as usize];
                    if let Err(err) = reader.read_exact(&mut adc_buffer) {
                        error!("Couldn't read ADC2 buffer size of {}: {}", adcnum.len(), err);
                        continue;
                    }

                    let channels = match get_channels_from_buffer(
                        adcnum,
                        &adc_buffer,
                        &config_thread,
                        &mut position,
                        max_x,
                        max_y,
                    ) {
                        Ok(channels) => channels,
                        Err(_err) => {
                            error!("Couldn't get channels from buffer");
                            continue;
                        }
                    };

                    for (_name, channel_result) in channels.iter() {
                        dataset[[position.y as usize, position.x as usize, *channel_result as usize]] += 1;
                    }
                }
                _ => {
                    continue;
                }
            }
        }

        return Ok((dataset, total_events, timer_events));
    });

    for position in rx {
        pb.set_position(position);
    }

    let (dataset, total_events, timer_events) = match handle_dataset.join().expect("Error getting dataset thread") {
        Ok(dataset) => dataset,
        Err(_err) => {
            error!("Error parsing the file");
            return Err("Error parsing the file");
        }
    };

    let mut nb_events: HashMap<String, u32> = HashMap::new();

    let mut parsing_result = ParsingResult {
        datasets: vec![],
        computed_datasets: vec![],
        attributes: HashMap::new(),
    };

    // Add acquisition time to attributes
    let acquisition_time = format_milliseconds(timer_events * timer_reduce);
    parsing_result.add_attr("acquisition_time".to_string(), acquisition_time.to_owned());
    parsing_result.add_attr("map_size_width".to_string(), map_size.width.to_string().to_owned());
    parsing_result.add_attr("map_size_height".to_string(), map_size.height.to_string().to_owned());
    parsing_result.add_attr("pen_size".to_string(), map_size.pen_size.to_string().to_owned());
    parsing_result.add_attr(
        "pixel_size_width".to_string(),
        map_size.pixel_size_width.to_string().to_owned(),
    );
    parsing_result.add_attr(
        "pixel_size_height".to_string(),
        map_size.pixel_size_height.to_string().to_owned(),
    );

    for (name, detector) in config.detectors.iter() {
        let slice_dset = get_slice_from_detector(name, detector, &dataset, &config);

        let nb_events_in_detector = slice_dset.iter().sum();
        nb_events.insert(name.to_string(), nb_events_in_detector);

        if nb_events_in_detector > 0 {
            let mut attributes = HashMap::new();

            if let Some(exp_info) = exp_info.clone() {
                if let Some(filter) = exp_info.get_filter_for_detector(name) {
                    attributes.insert("filter".to_string(), filter);
                }
            }

            let data = LSTData {
                name: name.to_string(),
                attributes,
                data: slice_dset,
            };
            parsing_result.datasets.push(data);
        }
    }

    for (name, detectors) in config.computed_detectors.iter() {
        let (computed_dataset, used_detectors) =
            generate_computed_dataset(&name, &detectors, &config, &map_size, &parsing_result);

        let nb_events_in_detector: u32 = computed_dataset.iter().sum();
        nb_events.insert(name.to_string(), nb_events_in_detector);

        // If the computed detector has events and is composed from at least 2 detectors
        if nb_events_in_detector > 0 && used_detectors.len() > 1 {
            let dset_name = used_detectors.join("+");
            let mut attributes = HashMap::new();

            if let Some(exp_info) = exp_info.clone() {
                for detector_name in used_detectors {
                    if let Some(filter) = exp_info.get_filter_for_detector(&detector_name) {
                        let key = format!("{}_filter", detector_name.to_lowercase());
                        attributes.insert(key, filter);
                    }
                }
            }

            let data = LSTData {
                name: dset_name.to_string(),
                attributes,
                data: computed_dataset,
            };
            parsing_result.computed_datasets.push(data);
        }
    }

    // Add the data from the ExpInfo to the parsing_result attributes
    if let Some(exp_info) = exp_info {
        parsing_result.add_attr("particle".to_string(), exp_info.particle);
        parsing_result.add_attr("beam_energy".to_string(), exp_info.beam_energy);
        debug!("ExpInfo metadata added");
    }

    info!("Acquisition time: {}", acquisition_time);
    info!("Nb events: {:?}", nb_events);
    info!("Total events: {total_events}");

    Ok(parsing_result)
}

/// For a given computed detector, get the used detectors and generate the dataset
fn generate_computed_dataset(
    name: &String,
    detectors: &Vec<String>,
    config: &LstConfig,
    map_size: &MapSize,
    parsing_result: &ParsingResult,
) -> (LSTDataset, Vec<String>) {
    let max_channels = config.get_max_channels_for_computed_detector(name);

    let mut computed_dataset: LSTDataset = Array3::zeros((
        map_size.get_max_y() as usize,
        map_size.get_max_x() as usize,
        max_channels as usize,
    ));
    let mut used_detectors: Vec<String> = Vec::new();

    for detector in detectors {
        let dset = match parsing_result.get_dataset(detector) {
            Some(dset) => dset,
            None => {
                error!("Couldn't get dataset {} for computed detector {}", detector, name);
                continue;
            }
        };

        used_detectors.push(detector.to_string());
        add_data_to_ndarray(&mut computed_dataset, &dset.data);
    }

    debug!("{} dataset shape: {:?}", name, computed_dataset.shape());

    return (computed_dataset, used_detectors);
}

fn get_slice_from_detector(name: &String, detector: &Detector, dataset: &LSTDataset, config: &LstConfig) -> LSTDataset {
    let floor = config.get_floor_for_detector_name(name) as usize;
    let offset = floor + detector.channels as usize;
    return dataset.slice(s![.., .., floor..offset]).to_owned();
}

fn get_channels_from_buffer(
    adcnum: Vec<u32>,
    buffer: &[u8],
    config: &LstConfig,
    position: &mut Position,
    max_x: i64,
    max_y: i64,
) -> Result<HashMap<String, u32>, &'static str> {
    let mut channels: HashMap<String, u32> = HashMap::new();
    #[allow(unused_assignments)] // False positive
    let mut adc_buffer = [0; 2];

    for (i, adc) in adcnum.iter().enumerate() {
        let adc_buffer_result = buffer[i * 2..i * 2 + 2].try_into();
        adc_buffer = match adc_buffer_result {
            Ok(adc_buffer) => adc_buffer,
            Err(_err) => {
                return Err("Couldn't convert buffer to adc_buffer");
            }
        };

        let int_value = u16::from_le_bytes(adc_buffer);

        if *adc == config.x && i64::from(int_value) < max_x {
            position.x = int_value;
        } else if *adc == config.y && i64::from(int_value) < max_y {
            position.y = int_value;
        } else {
            if let Some((name, detector, floor)) = config.get_detector_and_floor_for_adc(*adc) {
                if int_value > 0 {
                    let channel = std::cmp::min(u32::from(int_value), detector.channels - (1 as u32));
                    channels.insert(name.to_string(), channel + floor);
                }
            }
        }
    }

    return Ok(channels);
}

/// Read the LST header up to the [LISTDATA] keyword
/// Return a MapSize and an optional ExpInfo
fn read_header(reader: &mut BufReader<File>) -> Result<(MapSize, Option<ExpInfo>, u32), &'static str> {
    let mut map_size: Option<MapSize> = None;
    let mut exp_info: Option<ExpInfo> = None;
    let mut timer_reduce: u32 = 0;

    loop {
        let mut line = String::new();
        let bytes_read = reader.read_line(&mut line).expect("Couldn't read line");
        let content = line.trim();

        if content.contains("Map size") {
            map_size = MapSize::parse(content);
        }

        if content.contains("Exp.Info") {
            exp_info = ExpInfo::parse(content);
        }

        if content.contains("timerreduce") {
            if let Some(value) = content.split("=").collect::<Vec<&str>>().last() {
                timer_reduce = value.parse::<u32>().unwrap_or(0);
            }
        }

        if bytes_read == 0 || content.contains("[LISTDATA]") {
            // Done reading the header
            break;
        }
    }

    if let Some(map_size) = map_size {
        return Ok((map_size, exp_info, timer_reduce));
    }

    return Err("Couldn't read header");
}
