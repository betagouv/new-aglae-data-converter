use pyo3::{prelude::*, types::PyModule, wrap_pyfunction, Py, PyResult, Python};
use std::path;

mod converter;
use converter::{config::Config, models::ParsingResult};

/// Parse a LST file and write the result to a new file with the same name
///
/// Args:
///    file_path (str): Path to the LST file
///    output (str): Path to the output file
///    config (Config): Configuration for the conversion
///
/// Returns:
///   None
///
/// Raises:
///  PyException: If the conversion fails
#[pyfunction]
#[pyo3(signature = (file_path, config), text_signature = "(file_path, config)")]
fn parse_lst(file_path: String, config: Config) -> PyResult<Py<ParsingResult>> {
    let filepath = path::Path::new(&file_path);

    Python::with_gil(|py| match converter::parse_lst(filepath, config) {
        Ok(parsing_result) => Py::new(py, parsing_result),
        Err(err) => Err(PyErr::new::<pyo3::exceptions::PyException, _>(err)),
    })
}

#[pymodule]
fn lstrs(_py: Python, m: &PyModule) -> PyResult<()> {
    pyo3_log::init();

    m.add_function(wrap_pyfunction!(parse_lst, m)?)?;
    m.add_class::<converter::config::Detector>()?;
    m.add_class::<converter::config::ComputedDetector>()?;
    m.add_class::<converter::config::Config>()?;
    m.add_class::<converter::models::LSTData>()?;
    m.add_class::<converter::models::ParsingResult>()?;

    Ok(())
}
