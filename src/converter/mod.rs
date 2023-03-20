use std::{fs::File, path, io::{BufReader, BufRead, Seek, Read, SeekFrom}, time::Instant, result::Result, collections::HashMap};
use log::{info, error};
use ndarray::s;

pub mod config;
use config::LstConfig;

mod models;
use models::{MapSize, ExpInfo};

mod events;
use events::LstEvent;

#[derive(Debug, Clone, Copy)]
struct Position {
    x: u16,
    y: u16,
}

pub fn parse_lst(file_path: &path::Path, output: &path::Path, config: LstConfig) -> std::io::Result<()> {
    let filename = file_path.file_stem().expect("Cound't get filename").to_str().expect("Couldn't convert filename to str");

    info!("File to parse: {:?}", file_path);

    let file = File::open(file_path).expect("Error opening file");
    let mut reader = BufReader::new(file);

    let (map_size, exp_info) = read_header(&mut reader).unwrap();
    info!("Map size: {:?}", map_size);
    if let Some(exp_info) = exp_info {
        info!("Exp info: {:?}", exp_info);
    }

    let max_x = map_size.get_max_x();
    let max_y = map_size.get_max_y();

    let mut dataset = config.create_big_dataset(max_x, max_y);

    let mut total_events = 0;
    let mut total_timer_events = 0;

    let mut buffer = [0; 4];
    let mut position: Position = Position { x: 0, y: 0 };
    
    #[allow(unused_assignments)] // False positive (I think)
    let mut binary_value: u32 = 0;

    let parsing_started_at = Instant::now();

    // Read 4 bytes at a time
    loop {
        if let Err(_err) = reader.read_exact(&mut buffer) {
            break;
        }

        binary_value = u32::from_le_bytes(buffer);
        match LstEvent::inspect(binary_value) {
            Some(LstEvent::Timer) => {
                total_timer_events += 1;
                continue;
            },
            Some(LstEvent::Adc(has_dummy_word)) => {
                total_events += 1;

                if has_dummy_word {
                    // Dummy word was inserted, read 2 bytes
                    reader.seek(SeekFrom::Current(2))?;
                }

                let adcnum = get_adcnum(binary_value);
                let mut adc_buffer = vec![0; adcnum.len() * 2 as usize];
                if let Err(_err) = reader.read_exact(&mut adc_buffer) {
                    error!("Couldn't read ADC2 buffer");
                }

                let channels_results = get_channels_from_buffer(adcnum, &adc_buffer, &config, &mut position, max_x, max_y);
                let channels = match channels_results {
                    Ok(channels) => channels,
                    Err(_err) => {
                        error!("Couldn't get channels from buffer");
                        continue;
                    }
                };

                for (name, channel_result) in channels.iter() {
                    let floor = config.get_floor_for_detector_name(name);
                    dataset[[position.x as usize, position.y as usize, floor as usize + *channel_result as usize]] += 1;
                }
            },
            _ => {
                continue;
            },
        }
    }

    let parsing_duration = parsing_started_at.elapsed();
    println!("Parsing took {:?}", parsing_duration);

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
        let floor = config.get_floor_for_detector_name(name) as usize;
        let offset = floor + detector.channels as usize;
        let slice_dset = dataset.slice(s![.., .., floor..offset]).to_owned();

        let nb_events_in_detector = slice_dset.iter().sum();
        nb_events.insert(name.to_string(), nb_events_in_detector);

        if nb_events_in_detector > 0 {
            let builder = data_group.new_dataset_builder().deflate(4);
            let dset_name = &name[..];
            builder.with_data(&slice_dset).create(dset_name).expect("Couldn't create the dataset");
        }
    }

    info!("Nb events: {:?}", nb_events);
    info!("Total timer events: {total_timer_events}");
    info!("Total events: {total_events}");

    Ok(())
}

fn get_channels_from_buffer(adcnum: Vec<u32>, buffer: &[u8], config: &LstConfig, position: &mut Position, max_x: i64, max_y: i64) -> Result<HashMap<String, u32>, &'static str> {
    let mut channels: HashMap<String, u32> = HashMap::new();
    #[allow(unused_assignments)] // False positive
    let mut adc_buffer = [0; 2];

    for (i, adc) in adcnum.iter().enumerate() {
        let adc_buffer_result = buffer[i*2..i*2+2].try_into();
        adc_buffer = match adc_buffer_result {
            Ok(adc_buffer) => adc_buffer,
            Err(_err) => {
                return Err("Couldn't convert buffer to adc_buffer");
            },
        };

        let int_value = u16::from_le_bytes(adc_buffer);

        if *adc == config.x && i64::from(int_value) < max_x {
            position.x = int_value;
        } else if *adc == config.y && i64::from(int_value) < max_y {
            position.y = int_value;
        } else {
            if let Some((name, detector)) = config.get_detector_name_from_adc(*adc) {
                if int_value > 0 {
                    let channel = std::cmp::min(u32::from(int_value), detector.channels - (1 as u32));
                    channels.insert(name.to_string(), channel);
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
