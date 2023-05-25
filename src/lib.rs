use numpy::{PyArray3, ToPyArray};
use pyo3::{prelude::*, types::PyModule, wrap_pyfunction, Py, PyResult, Python};
use std::{collections::HashMap, path};

mod converter;
use converter::config::LstConfig;

#[pyclass(name = "LSTData")]
#[derive(Clone, Debug)]
pub struct PyLSTData {
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub attributes: HashMap<String, String>,
    #[pyo3(get, set)]
    pub data: Py<PyArray3<u32>>,
}

#[pymethods]
impl PyLSTData {
    #[new]
    fn py_new(name: String, attributes: HashMap<String, String>, data: Py<PyArray3<u32>>) -> Self {
        PyLSTData { name, attributes, data }
    }
}

#[pyclass(name = "ParsingResult")]
#[derive(Debug)]
pub struct PyParsingResult {
    #[pyo3(get, set)]
    pub attributes: HashMap<String, String>,
    #[pyo3(get, set)]
    pub datasets: Vec<PyLSTData>,
    #[pyo3(get, set)]
    pub computed_datasets: Vec<PyLSTData>,
}

#[pymethods]
impl PyParsingResult {
    #[new]
    fn py_new(
        attributes: HashMap<String, String>,
        datasets: Vec<PyLSTData>,
        computed_datasets: Vec<PyLSTData>,
    ) -> Self {
        PyParsingResult {
            attributes,
            datasets,
            computed_datasets,
        }
    }
}

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
#[pyo3(signature = (file_path, config), text_signature = "(file_path, config)")]
fn parse_lst(file_path: String, config: LstConfig) -> PyResult<Py<PyParsingResult>> {
    let filepath = path::Path::new(&file_path);

    Python::with_gil(|py| {
        let convert_result = converter::parse_lst(filepath, config);
        match convert_result {
            Ok(parsing_result) => {
                let parsed_results = Py::new(
                    py,
                    PyParsingResult::py_new(
                        parsing_result.attributes.to_owned(),
                        parsing_result
                            .datasets
                            .iter()
                            .map(|dset| {
                                PyLSTData::py_new(
                                    dset.name.to_string(),
                                    dset.attributes.to_owned(),
                                    dset.data.to_pyarray(py).to_owned(),
                                )
                            })
                            .collect(),
                        parsing_result
                            .computed_datasets
                            .iter()
                            .map(|dset| {
                                PyLSTData::py_new(
                                    dset.name.to_string(),
                                    dset.attributes.to_owned(),
                                    dset.data.to_pyarray(py).to_owned(),
                                )
                            })
                            .collect(),
                    ),
                )
                .unwrap();

                Ok(parsed_results)
            }
            Err(err) => Err(PyErr::new::<pyo3::exceptions::PyException, _>(err)),
        }
    })
}

#[pymodule]
fn lstrs(_py: Python, m: &PyModule) -> PyResult<()> {
    pyo3_log::init();

    m.add_function(wrap_pyfunction!(parse_lst, m)?)?;
    m.add_class::<converter::config::Detector>()?;
    m.add_class::<converter::config::LstConfig>()?;
    m.add_class::<PyLSTData>()?;
    m.add_class::<PyParsingResult>()?;

    Ok(())
}
