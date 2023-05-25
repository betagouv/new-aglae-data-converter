use ndarray::Array3;

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

pub type LSTDataset = Array3<u32>;

#[derive(Debug, Clone)]
pub struct ParsingResult {
    pub datasets: Vec<LSTDataset>,
}
