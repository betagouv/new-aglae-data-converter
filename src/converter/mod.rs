use indicatif::{ProgressBar, ProgressState, ProgressStyle};
use log::{debug, error, info};
use ndarray::{s, Array3};
use std::{
    collections::HashMap,
    fmt::Write,
    fs::File,
    io::{BufRead, BufReader, Read, Seek, SeekFrom},
    path,
    result::Result,
    sync::mpsc,
    thread,
};

pub mod config;
use config::{Detector, LstConfig};

mod models;
use models::{ExpInfo, MapSize};

mod events;
use events::LstEvent;

#[derive(Debug, Clone, Copy)]
struct Position {
    x: u16,
    y: u16,
}

pub fn parse_lst(file_path: &path::Path, output: &path::Path, config: LstConfig) -> std::io::Result<()> {
    let filename = file_path
        .file_stem()
        .expect("Cound't get filename")
        .to_str()
        .expect("Couldn't convert filename to str");

    info!("File to parse: {:?}", file_path);
    info!("Config used: {:?}", config);

    let file = File::open(file_path).expect("Error opening file");
    // Get the total size of the file
    let file_size = file.metadata().unwrap().len();

    let mut reader = BufReader::new(file);

    let (map_size, exp_info) = read_header(&mut reader).unwrap();
    info!("Map size: {:?}", map_size);
    if let Some(exp_info) = exp_info.clone() {
        info!("Exp info: {:?}", exp_info);
    }

    let max_x = map_size.get_max_x();
    let max_y = map_size.get_max_y();

    let pb = ProgressBar::new(file_size);
    pb.set_style(
        ProgressStyle::with_template(
            "{spinner:.green}  [{elapsed_precise}] [{wide_bar:.cyan/blue}] {bytes}/{total_bytes} ({eta})",
        )
        .unwrap()
        .with_key("eta", |state: &ProgressState, w: &mut dyn Write| {
            write!(w, "{:.1}s", state.eta().as_secs_f64()).unwrap()
        })
        .progress_chars("#>-"),
    );

    let (tx, rx) = mpsc::channel();

    let config_thread = config.clone();
    let mut dataset = config_thread.create_big_dataset(max_x, max_y);
    debug!("Dataset created: {:?}", dataset.shape());

    // Launch thread to parse the file
    let handle_dataset = thread::spawn(move || -> Result<(Array3<u32>, i32), &str> {
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
                    let current_position = reader.seek(SeekFrom::Current(0)).expect("Couldn't read position");
                    if let Err(err) = tx.send(current_position) {
                        println!("Couldn't send position: {}", err);
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
                    if let Err(_err) = reader.read_exact(&mut adc_buffer) {
                        error!("Couldn't read ADC2 buffer");
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

        return Ok((dataset, total_events));
    });

    for position in rx {
        pb.set_position(position);
    }

    let (dataset, total_events) = match handle_dataset.join().expect("Error getting dataset thread") {
        Ok(dataset) => dataset,
        Err(_err) => {
            error!("Error parsing the file");
            return Ok(());
        }
    };

    let mut nb_events: HashMap<String, u32> = HashMap::new();
    let file_builder = hdf5::FileBuilder::new();

    if !output.exists() {
        std::fs::create_dir(output)?;
    }

    let h5_file_path = output.join(format!("{}.hdf5", filename));

    let file = file_builder.create(h5_file_path).expect("Couldn't create the file");
    let data_group = file.create_group("data").expect("Couldn't create the group");

    // // let mut z_index = 0;
    for (name, detector) in config.detectors.iter() {
        let slice_dset = get_slice_from_detector(name, detector, &dataset, &config);

        let nb_events_in_detector = slice_dset.iter().sum();
        nb_events.insert(name.to_string(), nb_events_in_detector);

        if nb_events_in_detector > 0 {
            let builder = data_group.new_dataset_builder().deflate(4);
            let dset_name = &name[..];
            if let Err(err) = builder.with_data(&slice_dset).create(dset_name) {
                error!("Couldn't create dataset {}: {}", dset_name, err);
            }
        }
    }

    for (name, detectors) in config.computed_detectors.iter() {
        let (computed_dataset, used_detectors) =
            generate_computed_dataset(&name, &detectors, &config, &map_size, &data_group);

        let nb_events_in_detector: u32 = computed_dataset.iter().sum();
        nb_events.insert(name.to_string(), nb_events_in_detector);

        if nb_events_in_detector > 0 {
            let builder = data_group.new_dataset_builder().deflate(4);
            let dset_name = &name[..];
            let created_dset = match builder.with_data(&computed_dataset).create(dset_name) {
                Ok(created_dset) => created_dset,
                Err(err) => {
                    error!("Couldn't create the dataset {}: {}", name, err);
                    continue;
                }
            };

            let attrs = match created_dset.new_attr::<hdf5::types::VarLenUnicode>().create("sources") {
                Ok(attrs) => attrs,
                Err(err) => {
                    error!("Couldn't create the attributes for {}: {}", name, err);
                    continue;
                }
            };

            // Add used detectors to the HDF5 attibutes
            let used_detectors_value: hdf5::types::VarLenUnicode = used_detectors.join(", ")[..].parse().unwrap();
            if let Err(err) = attrs.write_scalar(&used_detectors_value) {
                error!("Couldn't write the attributes for {}: {}", name, err);
            }
        }
    }

    // Add the data from the ExpInfo to the data_group attributes
    if let Some(exp_info) = exp_info {
        if let Err(err) = add_exp_info_attributes(exp_info.clone(), &data_group) {
            error!("Couldn't add ExpInfo attributes: {}", err);
        }
    }

    info!("Nb events: {:?}", nb_events);
    info!("Total events: {total_events}");

    Ok(())
}

fn add_exp_info_attributes(exp_info: ExpInfo, group: &hdf5::Group) -> Result<(), hdf5::Error> {
    debug!("Adding ExpInfo");
    for (key, value) in exp_info.to_array_tuple() {
        debug!("{}: {}", key, value);
        let attr = group.new_attr::<hdf5::types::VarLenUnicode>().create(key)?;
        let parsed_value: hdf5::types::VarLenUnicode = match value.parse() {
            Ok(parsed_value) => parsed_value,
            Err(err) => {
                let formatted_error = format!("Error while parsing the value for {}: {}", key, err);
                return Err(hdf5::Error::Internal(formatted_error));
            }
        };
        attr.write_scalar(&parsed_value)?;
    }
    debug!("ExpInfo metadata added");
    Ok(())
}

/// For a given computed detector, get the used detectors and generate the dataset
fn generate_computed_dataset(
    name: &String,
    detectors: &Vec<String>,
    config: &LstConfig,
    map_size: &MapSize,
    data_group: &hdf5::Group,
) -> (Array3<u32>, Vec<String>) {
    let max_channels = config.get_max_channels_for_computed_detector(name);

    let mut computed_dataset: Array3<u32> = Array3::zeros((
        map_size.get_max_y() as usize,
        map_size.get_max_x() as usize,
        max_channels as usize,
    ));
    let mut used_detectors: Vec<String> = Vec::new();

    for detector in detectors {
        let dset = match data_group.dataset(&detector) {
            Ok(dset) => dset,
            Err(err) => {
                error!(
                    "Couldn't get dataset {} for computed detector {}: {}",
                    detector, name, err
                );
                continue;
            }
        };

        let dset_data: Array3<u32> = match dset.read() {
            Ok(dset_data) => dset_data,
            Err(err) => {
                error!(
                    "Couldn't read dataset {} for computed detector {}: {}",
                    detector, name, err
                );
                continue;
            }
        };

        used_detectors.push(detector.to_string());
        add_data_to_ndarray(&mut computed_dataset, &dset_data);
    }

    debug!("{} dataset shape: {:?}", name, computed_dataset.shape());

    return (computed_dataset, used_detectors);
}

fn add_data_to_ndarray(array1: &mut Array3<u32>, array2: &Array3<u32>) {
    for (x, axis_1) in array2.outer_iter().enumerate() {
        for (y, axis_2) in axis_1.outer_iter().enumerate() {
            for (z, _) in axis_2.outer_iter().enumerate() {
                array1[[x, y, z]] += array2[[x, y, z]];
            }
        }
    }
}

fn get_slice_from_detector(
    name: &String,
    detector: &Detector,
    dataset: &Array3<u32>,
    config: &LstConfig,
) -> Array3<u32> {
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

fn read_header(reader: &mut BufReader<File>) -> Result<(MapSize, Option<ExpInfo>), &'static str> {
    let mut map_size: Option<MapSize> = None;
    let mut exp_info: Option<ExpInfo> = None;

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

        if bytes_read == 0 || content.contains("[LISTDATA]") {
            // Done reading the header
            break;
        }
    }

    if let Some(map_size) = map_size {
        return Ok((map_size, exp_info));
    }

    return Err("Couldn't read header");
}

fn get_adcnum(binary_value: u32) -> Vec<u32> {
    // We know there can be at most 16 values
    let mut adcnum: Vec<u32> = vec![];
    // println!("{binary_value:#034b}");
    // Get the value of the first 16 bits are 1
    for bits in 0..16 {
        let value_bin = 0b0000000000000001 << bits;
        if binary_value >> bits & 1 == 1 {
            adcnum.push(value_bin as u32);
        }
    }

    return adcnum;
}
