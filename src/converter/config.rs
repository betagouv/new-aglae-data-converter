use ndarray::Array3;
use pyo3::prelude::*;
use std::collections::{BTreeMap, HashMap};

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
    pub detectors: BTreeMap<String, Detector>,
    pub computed_detectors: HashMap<String, Vec<String>>,
    pub adcs: Vec<u32>,
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
        Array3::zeros((max_y as usize, max_x as usize, total_max_channels as usize))
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

    /// Get the detector name and the floor for a given ADC
    /// If no detector is found, None is returned
    pub fn get_detector_and_floor_for_adc(&self, adc: u32) -> Option<(&String, &Detector, u32)> {
        let mut floor: u32 = 0;
        for (name, detector) in self.detectors.iter() {
            if detector.adc == adc {
                return Some((name, detector, floor));
            }
            floor += detector.channels;
        }
        return None;
    }

    pub fn adc_exists(&self, adc: u32) -> bool {
        for (_, detector) in self.detectors.iter() {
            if detector.adc == adc {
                return true;
            }
        }
        return false;
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
        detectors: BTreeMap<String, Detector>,
        computed_detectors: HashMap<String, Vec<String>>,
    ) -> Self {
        let mut adcs: Vec<u32> = vec![x, y];

        for (_, detector) in detectors.iter() {
            adcs.push(detector.adc);
        }
        adcs.sort();

        LstConfig {
            x,
            y,
            detectors,
            computed_detectors,
            adcs,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn default_detectors() -> BTreeMap<String, Detector> {
        let mut detectors: BTreeMap<String, Detector> = BTreeMap::new();
        detectors.insert("HE1".to_string(), Detector { adc: 1, channels: 2048 });
        detectors.insert("HE2".to_string(), Detector { adc: 2, channels: 2048 });
        detectors.insert("HE3".to_string(), Detector { adc: 4, channels: 2048 });
        detectors.insert("HE4".to_string(), Detector { adc: 8, channels: 2048 });
        detectors.insert(
            "LE0".to_string(),
            Detector {
                adc: 16,
                channels: 2048,
            },
        );
        detectors.insert(
            "GAMMA".to_string(),
            Detector {
                adc: 32,
                channels: 4096,
            },
        );
        detectors.insert("RBS".to_string(), Detector { adc: 64, channels: 512 });
        detectors.insert(
            "GAMMA_20".to_string(),
            Detector {
                adc: 1024,
                channels: 4096,
            },
        );

        return detectors;
    }

    fn default_computed_detectors() -> HashMap<String, Vec<String>> {
        let mut computed_detectors: HashMap<String, Vec<String>> = HashMap::new();
        computed_detectors.insert(
            "HE10".to_string(),
            vec![
                "HE1".to_string(),
                "HE2".to_string(),
                "HE3".to_string(),
                "HE4".to_string(),
            ],
        );
        computed_detectors.insert("HE11".to_string(), vec!["HE1".to_string(), "HE2".to_string()]);
        computed_detectors.insert("HE12".to_string(), vec!["HE3".to_string(), "HE4".to_string()]);
        computed_detectors.insert(
            "HE13".to_string(),
            vec!["HE1".to_string(), "HE2".to_string(), "HE3".to_string()],
        );

        return computed_detectors;
    }

    fn default_config() -> LstConfig {
        LstConfig::py_new(256, 512, default_detectors(), default_computed_detectors())
    }

    #[test]
    fn test_lst_config_adcs() {
        let default = default_config();

        assert_eq!(default.adcs, &[1, 2, 4, 8, 16, 32, 64, 256, 512, 1024]);
    }

    #[test]
    fn test_adc_exists() {
        let default = default_config();

        let mut adc = default.adc_exists(1);
        assert_eq!(adc, true);

        adc = default.adc_exists(2);
        assert_eq!(adc, true);

        adc = default.adc_exists(16);
        assert_eq!(adc, true);

        adc = default.adc_exists(1024);
        assert_eq!(adc, true);

        adc = default.adc_exists(12);
        assert_eq!(adc, false);

        adc = default.adc_exists(88);
        assert_eq!(adc, false)
    }

    #[test]
    fn test_create_big_dataset() {
        let default = default_config();
        let dataset = default.create_big_dataset(40, 60);

        assert_eq!(dataset.shape(), &[60, 40, 18944])
    }

    #[test]
    fn test_get_floor_for_detector_name() {
        let default = default_config();

        let mut floor: u32 = 0;
        for (index, (name, _detector)) in default.detectors.iter().enumerate() {
            let new_floor = default.get_floor_for_detector_name(name);
            if index == 0 {
                assert_eq!(new_floor, 0);
            } else {
                let (_name, previous_detector) = default.detectors.iter().nth(index - 1).unwrap();
                assert_eq!(new_floor, floor + previous_detector.channels);
            }
            floor = new_floor;
        }
    }
}
