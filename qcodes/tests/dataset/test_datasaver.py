import pytest
import os
import tempfile
import qcodes as qc
from qcodes.dataset.measurements import DataSaver
from qcodes.dataset.sqlite_base import connect, init_db

CALLBACK_COUNT = 0
CALLBACK_RUN_ID = None
CALLBACK_SNAPSHOT = None

# These fixture can't be imported from test_dataset_basic because Codacy/PR Quality Review will think they are unused.
@pytest.fixture(scope="function")
def empty_temp_db():
    # create a temp database for testing
    with tempfile.TemporaryDirectory() as tmpdirname:
        qc.config["core"]["db_location"] = os.path.join(tmpdirname, 'temp.db')
        qc.config["core"]["db_debug"] = True
        # this is somewhat annoying but these module scope variables
        # are initialized at import time so they need to be overwritten
        qc.dataset.experiment_container.DB = qc.config["core"]["db_location"]
        qc.dataset.data_set.DB = qc.config["core"]["db_location"]
        qc.dataset.experiment_container.debug_db = qc.config["core"]["db_debug"]
        _c = connect(qc.config["core"]["db_location"], qc.config["core"]["db_debug"])
        init_db(_c)
        _c.close()
        yield


@pytest.fixture(scope='function')
def experiment(empty_temp_db):
    e = qc.new_experiment("test-experiment", sample_name="test-sample")
    yield e
    e.conn.close()


def callback(result_list, data_set_len, state, run_id, snapshot):
    """
    default_callback example function implemented in the Web UI.
    """
    global CALLBACK_COUNT, CALLBACK_RUN_ID, CALLBACK_SNAPSHOT
    CALLBACK_COUNT += 1
    CALLBACK_RUN_ID = run_id
    CALLBACK_SNAPSHOT = snapshot


def reset_callback_globals():
    global CALLBACK_COUNT, CALLBACK_RUN_ID, CALLBACK_SNAPSHOT
    CALLBACK_COUNT = 0
    CALLBACK_RUN_ID = None
    CALLBACK_SNAPSHOT = None


def test_default_callback(experiment):
    """
    The Web UI needs to know the results of an experiment with the metadata.
    So a default_callback class variable is set by the Web UI with a callback to introspect the data.
    """
    test_set = None
    reset_callback_globals()

    try:
        DataSaver.default_callback = {
            'run_tables_subscription_callback': callback,
            'run_tables_subscription_min_wait': 1,
            'run_tables_subscription_min_count': 1,
        }
        test_set = qc.new_data_set("test-dataset")
        test_set.add_metadata('snapshot', 123)
        DataSaver(dataset=test_set, write_period=0, parameters={})
        test_set.mark_complete()
        assert CALLBACK_SNAPSHOT == 123
        assert CALLBACK_RUN_ID > 0
        assert CALLBACK_COUNT > 0
    finally:
        DataSaver.default_callback = None
        if test_set is not None:
            test_set.conn.close()
