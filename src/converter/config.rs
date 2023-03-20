use ndarray::Array3;
use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
#[derive(Debug, Clone)]
pub struct Detector {
    pub adc: u32,
    pub channels: u32,
}

#[pymethods]
impl Detector {
    #[new]
    fn py_new(adc: u32, channels: u32) -> Self {
        Detector { adc, channels }
    }
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct LstConfig {
    pub x: u32,
    pub y: u32,
    pub detectors: HashMap<String, Detector>,
    pub computed_detectors: HashMap<String, Vec<String>>,
}

impl LstConfig {
    pub fn get_detector_name_from_adc(&self, adc: u32) -> Option<(&String, &Detector)> {
        for (name, detector) in self.detectors.iter() {
            if detector.adc == adc {
                return Some((name, detector));
            }
        }
        return None;
    }

    pub fn create_big_dataset(&self, max_x: i64, max_y: i64) -> Array3<u32> {
        let total_max_channels = self
            .detectors
            .iter()
            .fold(0, |acc, (_, detector)| acc + detector.channels);
        Array3::zeros((max_x as usize, max_y as usize, total_max_channels as usize))
    }

    pub fn get_floor_for_detector_name(&self, detector_name: &String) -> u32 {
        let mut floor: u32 = 0;
        for (name, detector) in self.detectors.iter() {
            if name == detector_name {
                return floor;
            }
            floor += detector.channels;
        }
        return 0;
    }

    /// Get the maximum number of channels for a computed detector
    /// If no detectors are found, 0 is returned
    pub fn get_max_channels_for_computed_detector(&self, computed_detector_name: &String) -> u32 {
        return self
            .detectors
            .iter()
            .filter_map(|(name, detector)| {
                if self.computed_detectors[computed_detector_name].contains(name) {
                    Some(detector.channels)
                } else {
                    None
                }
            })
            .max()
            .unwrap_or(0);
    }
}

#[pymethods]
impl LstConfig {
    #[new]
    fn py_new(
        x: u32,
        y: u32,
        detectors: HashMap<String, Detector>,
        computed_detectors: HashMap<String, Vec<String>>,
    ) -> Self {
        LstConfig {
            x,
            y,
            detectors,
            computed_detectors,
        }
    }
}
