pub enum LstEvent {
    Timer,
    Synchron,
    Adc(bool),
}

impl LstEvent {
    pub fn inspect(binary_value: u32) -> Option<LstEvent> {
        if binary_value >> 16 & 0xFFFF == 0x4000 {
            return Some(LstEvent::Timer);
        } else if binary_value == 0xFFFFFFFF {
            return Some(LstEvent::Synchron);
        } else if ((binary_value >> 30) & 1) == 1 {
            // Not an event
            return None;
        }

        let has_dummy_word = binary_value >> 31 & 1 == 1;
        return Some(LstEvent::Adc(has_dummy_word));
    }
}