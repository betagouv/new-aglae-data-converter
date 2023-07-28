use lazy_static::lazy_static;
use ndarray::Array3;
use numpy::PyArray3;
use pyo3::{prelude::*, PyResult, Python};
use regex::Regex;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct MapSize {
    pub width: u32,
    pub height: u32,
    pub pixel_size_width: u32,
    pub pixel_size_height: u32,
    pub pen_size: u32,
}

impl MapSize {
    pub fn parse(content: &str) -> Option<Self> {
        if let Some(map_params) = content.split(":").collect::<Vec<&str>>().last() {
            let params = map_params.split(",").collect::<Vec<&str>>();
            let width = params[0].parse::<u32>().unwrap_or(0);
            let height = params[1].parse::<u32>().unwrap_or(0);
            let pixel_size_width = params[2].parse::<u32>().unwrap_or(0);
            let pixel_size_height = params[3].parse::<u32>().unwrap_or(0);
            let pen_size = params[4].parse::<u32>().unwrap_or(0);

            return Some(MapSize {
                width,
                height,
                pixel_size_width,
                pixel_size_height,
                pen_size,
            });
        }

        return None;
    }

    pub fn get_max_x(&self) -> i64 {
        return (self.width as f64 / self.pixel_size_width as f64).round() as i64;
    }

    pub fn get_max_y(&self) -> i64 {
        return (self.height as f64 / self.pixel_size_height as f64).round() as i64;
    }

    pub fn is_empty(&self) -> bool {
        return self.width == 0
            && self.height == 0
            && self.pixel_size_width == 0
            && self.pixel_size_height == 0
            && self.pen_size == 0;
    }
}

#[derive(Debug, Clone)]
pub struct ExpInfo {
    pub particle: String,
    pub beam_energy: String,
    pub le0_filter: String,
    pub he1_filter: String,
    pub he2_filter: String,
    pub he3_filter: String,
    pub he4_filter: String,
}

impl ExpInfo {
    pub fn parse(content: &str) -> Option<ExpInfo> {
        if let Some(exp_params) = content.split(":").collect::<Vec<&str>>().last() {
            let params = exp_params.split(",").collect::<Vec<&str>>();
            let particle = params[0].to_string();
            let beam_energy = params[1].to_string();
            let le0_filter = params[2].to_string();
            let he1_filter = params[3].to_string();
            let he2_filter = params[4].to_string();
            let he3_filter = params[5].to_string();
            let he4_filter = params[6].to_string();

            return Some(ExpInfo {
                particle,
                beam_energy,
                le0_filter,
                he1_filter,
                he2_filter,
                he3_filter,
                he4_filter,
            });
        }

        return None;
    }

    pub fn get_filter_for_detector(&self, filter_name: &str) -> Option<String> {
        let filter = match filter_name {
            "LE0" => self.le0_filter.clone(),
            "HE1" => self.he1_filter.clone(),
            "HE2" => self.he2_filter.clone(),
            "HE3" => self.he3_filter.clone(),
            "HE4" => self.he4_filter.clone(),
            _ => return None,
        };

        return Some(filter);
    }
}

lazy_static! {
    static ref LST_HEADER_REGEX: Regex = Regex::new(r"(cmline\d{1,2}\=?\ )(?<cmd>[a-zA-Z0-9-.\ ]+)(:)").unwrap();
}

pub struct LSTHeader {
    pub map_size: MapSize,
    pub exp_info: Option<ExpInfo>,
    pub timer_reduce: u32,
    pub euphrosyne_project_name: Option<String>,
    pub run_name: Option<String>,
    pub euphrosyne_object_name: Option<String>,
    pub aglae_object_name: Option<String>,
    pub aglae_project_name: Option<String>,
    pub aglae_material: Option<String>,
}

impl LSTHeader {
    pub fn new() -> Self {
        LSTHeader {
            map_size: MapSize {
                width: 0,
                height: 0,
                pixel_size_width: 0,
                pixel_size_height: 0,
                pen_size: 0,
            },
            exp_info: None,
            timer_reduce: 0,
            euphrosyne_project_name: None,
            run_name: None,
            euphrosyne_object_name: None,
            aglae_object_name: None,
            aglae_project_name: None,
            aglae_material: None,
        }
    }

    fn parse_end_line(line: &str) -> Option<String> {
        if let Some(str) = line.split(":").last() {
            return Some(str.to_string());
        }
        return None;
    }

    pub fn parse_line(&mut self, line: &str) {
        let Some(el) = LST_HEADER_REGEX.captures(line) else {
            // log::debug!("No match found for line: {:?}", line);
            return;
        };

        match &el["cmd"] {
            "Map size" => {
                if let Some(map_size) = MapSize::parse(line) {
                    self.map_size = map_size;
                }
            }
            "Exp info" => {
                if let Some(exp_info) = ExpInfo::parse(line) {
                    self.exp_info = Some(exp_info);
                }
            }
            "Prj-Euphrosyne" => {
                self.euphrosyne_project_name = Self::parse_end_line(line);
            }
            "Run-Euphrosyne" => self.run_name = Self::parse_end_line(line),
            "Obj-Euphrosyne" => self.euphrosyne_object_name = Self::parse_end_line(line),
            "Obj-AGLAE" => self.aglae_object_name = Self::parse_end_line(line),
            "Prj-AGLAE" => self.aglae_project_name = Self::parse_end_line(line),
            "Material-AGLAE" => self.aglae_material = Self::parse_end_line(line),
            _ => {}
        }

        log::debug!("Found cmline to parse {:?}", &el["cmd"]);
    }
}

pub type LSTDataset = Array3<u32>;

#[pyclass]
#[derive(Debug, Clone)]
pub struct LSTData {
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub attributes: HashMap<String, String>,
    pub data: LSTDataset,
}

#[pymethods]
impl LSTData {
    #[getter]
    fn get_data(&self) -> PyResult<Py<PyArray3<u32>>> {
        Python::with_gil(|py| {
            let data = self.data.clone();
            let array = PyArray3::from_array(py, &data);
            return Ok(array.to_owned());
        })
    }
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct ParsingResult {
    #[pyo3(get, set)]
    pub datasets: Vec<LSTData>,
    #[pyo3(get, set)]
    pub computed_datasets: Vec<LSTData>,
    #[pyo3(get, set)]
    pub attributes: HashMap<String, String>,
}

impl ParsingResult {
    pub fn get_dataset(&self, name: &str) -> Option<&LSTData> {
        for dataset in &self.datasets {
            if dataset.name == name {
                return Some(dataset);
            }
        }
        return None;
    }

    pub fn add_attr(&mut self, key: String, value: String) {
        self.attributes.insert(key, value);
    }
}
