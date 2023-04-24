use hdf5;
use ndarray::Array3;

/// For a given 32 bits integer, return the list of detectors in it
/// ```
/// let adcnum = get_adcnum(2147484424);
/// assert_eq!(adcnum, [8, 256, 521]);
/// ```
pub fn get_adcnum(binary_value: u32) -> Vec<u32> {
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

//
pub fn add_data_to_ndarray(array1: &mut Array3<u32>, array2: &Array3<u32>) {
    for (x, axis_1) in array2.outer_iter().enumerate() {
        for (y, axis_2) in axis_1.outer_iter().enumerate() {
            for (z, _) in axis_2.outer_iter().enumerate() {
                array1[[x, y, z]] += array2[[x, y, z]];
            }
        }
    }
}

/// Helper function to write a string attribute to a group
pub fn write_attr(group: &hdf5::Group, key: &str, value: &String) -> Result<(), hdf5::Error> {
    let attr = group.new_attr::<hdf5::types::VarLenUnicode>().create(key)?;

    let parsed_value: hdf5::types::VarLenUnicode = match value.parse() {
        Ok(parsed_value) => parsed_value,
        Err(err) => {
            let formatted_error = format!("Error while parsing the value for {}: {}", key, err);
            return Err(hdf5::Error::Internal(formatted_error));
        }
    };

    attr.write_scalar(&parsed_value)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use ndarray::arr3;
    use std::fs;

    #[test]
    fn test_get_adcnum() {
        let mut adcnum = get_adcnum(2147484424);
        assert_eq!(adcnum, [8, 256, 512]);

        adcnum = get_adcnum(2147487520);
        assert_eq!(adcnum, [32, 256, 512, 1024, 2048]);
    }

    #[test]
    fn test_add_data_array() {
        let mut array_1: Array3<u32> = arr3(&[[[1, 2, 3], [6, 7, 8], [1, 2, 3]], [[1, 2, 3], [6, 7, 8], [1, 2, 3]]]);
        assert_eq!(array_1.shape(), &[2, 3, 3]);

        let array_2: Array3<u32> = arr3(&[[[1, 2, 3], [6, 7, 8], [1, 2, 3]], [[1, 2, 3], [6, 7, 8], [1, 2, 3]]]);
        assert_eq!(array_2.shape(), &[2, 3, 3]);

        add_data_to_ndarray(&mut array_1, &array_2);

        assert_eq!(array_1.shape(), &[2, 3, 3]);
        assert_eq!(
            array_1,
            arr3(&[
                [[2, 4, 6], [12, 14, 16], [2, 4, 6]],
                [[2, 4, 6], [12, 14, 16], [2, 4, 6]]
            ])
        );

        let array_3: Array3<u32> = arr3(&[[[1, 2, 3], [6, 7, 8], [1, 2, 3]], [[1, 2, 3], [6, 7, 8], [1, 2, 3]]]);
        assert_eq!(array_3.shape(), &[2, 3, 3]);

        add_data_to_ndarray(&mut array_1, &array_3);
        assert_eq!(array_1.shape(), &[2, 3, 3]);
        assert_eq!(
            array_1,
            arr3(&[
                [[3, 6, 9], [18, 21, 24], [3, 6, 9]],
                [[3, 6, 9], [18, 21, 24], [3, 6, 9]],
            ])
        );
    }

    #[test]
    fn test_writing_attributes() {
        let dataset = hdf5::File::create("test.h5").unwrap();
        let group = dataset.create_group("test_group").unwrap();

        let key: &str = "test_attr";
        let value: String = "Hello World".to_string();
        write_attr(&group, key, &value).unwrap();

        let test_attr = group.attr(key).unwrap();
        assert_eq!(
            test_attr
                .read_scalar::<hdf5::types::VarLenUnicode>()
                .unwrap()
                .parse::<String>()
                .unwrap(),
            value
        );

        fs::remove_file("test.h5").unwrap();
    }
}
