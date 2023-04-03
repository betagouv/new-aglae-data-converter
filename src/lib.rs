use pyo3::{prelude::*, types::PyModule, wrap_pyfunction, PyResult, Python};
use std::path;

mod converter;
use converter::config::LstConfig;

/// Parse a LST file and write the result to a new file with the same name
///
/// Args:
///    file_path (str): Path to the LST file
///    output (str): Path to the output file
///    config (LstConfig): Configuration for the conversion
///
/// Returns:
///   None
///
/// Raises:
///  PyException: If the conversion fails
#[pyfunction]
#[pyo3(signature = (file_path, output, config), text_signature = "(file_path, output, config)")]
fn parse_lst(file_path: String, output: String, config: LstConfig) -> PyResult<()> {
    let filepath = path::Path::new(&file_path);
    let outputpath = path::Path::new(&output);

    let convert_result = converter::parse_lst(filepath, outputpath, config);
    match convert_result {
        Ok(_) => Ok(()),
        Err(err) => Err(PyErr::new::<pyo3::exceptions::PyException, _>(err)),
    }
}

#[pymodule]
fn lstrs(_py: Python, m: &PyModule) -> PyResult<()> {
    pyo3_log::init();

    m.add_function(wrap_pyfunction!(parse_lst, m)?)?;
    m.add_class::<converter::config::Detector>()?;
    m.add_class::<converter::config::LstConfig>()?;

    Ok(())
}
