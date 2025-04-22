from datetime import datetime
import unittest
from EDemandService.EDemandService import CalculationServiceElectricityDemand
from dots_infrastructure.DataClasses import SimulatorConfiguration, TimeStepInformation
from dots_infrastructure.test_infra.InfluxDBMock import InfluxDBMock
from esdl.esdl_handler import EnergySystemHandler
import helics as h
import numpy as np

from dots_infrastructure import CalculationServiceHelperFunctions

BROKER_TEST_PORT = 23404
START_DATE_TIME = datetime(2024, 1, 1, 0, 0, 0)
SIMULATION_DURATION_IN_SECONDS = 960

def simulator_environment_e_connection():
    return SimulatorConfiguration("ElectricityDemand", ["a3b51e59-c961-4210-9637-d67e1e9e6aed"], "Mock-Econnection", "127.0.0.1", BROKER_TEST_PORT, "test-id", SIMULATION_DURATION_IN_SECONDS, START_DATE_TIME, "test-host", "test-port", "test-username", "test-password", "test-database-name", h.HelicsLogLevel.DEBUG, ["PVInstallation", "EConnection"])

class Test(unittest.TestCase):

    def setUp(self):
        CalculationServiceHelperFunctions.get_simulator_configuration_from_environment = simulator_environment_e_connection
        esh = EnergySystemHandler()
        esh.load_file("test.esdl")
        self.energy_system = esh.get_energy_system()

    def test_predict_demand(self):

        # Arrange
        service = CalculationServiceElectricityDemand()
        service.influx_connector = InfluxDBMock()
        service.init_calculation_service(self.energy_system)

        # # Execute
        ret_val = service.predict_demand({}, datetime(2020,9,1), TimeStepInformation(1,2), "a3b51e59-c961-4210-9637-d67e1e9e6aed", self.energy_system)

        # Assert
        expected_active_power_profile = [128.0000000006111, 147.9999999992287, 112.0000000009895, 123.9999999997962, 144.0000000002328, 131.9999999996071, 167.9999999996653, 148.0000000010477, 131.9999999996071, 111.9999999991705, 140.0000000012369, 131.9999999996071, 100.0000000003638, 75.9999999991123, 72.0000000001164, 56.0000000004947, 79.9999999999272, 75.9999999991123, 72.0000000001164, 76.0000000009313, 79.9999999999272, 75.9999999991123, 148.0000000010477, 152.0000000000436, 123.9999999997962, 135.999999998603, 144.0000000038708, 195.9999999999127, 871.9999999975698, 311.9999999998981, 291.9999999994616, 172.0000000004802, 175.9999999994761, 148.0000000010477, 147.9999999992287, 172.0000000004802, 183.9999999992869, 443.9999999995052, 172.0000000004802, 175.9999999994761, 172.0000000004802, 152.0000000000436, 148.0000000010477, 175.9999999994761, 155.9999999990395, 140.0000000012369, 167.9999999996653, 108.0000000001746, 83.9999999989231]
        pf = 0.95
        expected_reactive_power_profile = [np.sqrt(1-pf**2)/pf * p for p in expected_active_power_profile]
        self.assertListEqual(expected_active_power_profile, ret_val["active_power"])
        self.assertListEqual(expected_reactive_power_profile, ret_val["reactive_power"])

if __name__ == '__main__':
    unittest.main()
