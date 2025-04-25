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

def simulator_environment_e_demand():
    return SimulatorConfiguration("ElectricityDemand", ["25d212e5-ca5f-4a3d-9fb1-a5f024b2460a"], "Mock-Econnection", "127.0.0.1", BROKER_TEST_PORT, "test-id", SIMULATION_DURATION_IN_SECONDS, START_DATE_TIME, "test-host", "test-port", "test-username", "test-password", "test-database-name", h.HelicsLogLevel.DEBUG, ["PVInstallation", "EConnection"])

class Test(unittest.TestCase):

    def setUp(self):
        CalculationServiceHelperFunctions.get_simulator_configuration_from_environment = simulator_environment_e_demand
        esh = EnergySystemHandler()
        esh.load_file("test.esdl")
        self.energy_system = esh.get_energy_system()

    def test_predict_demand(self):

        # Arrange
        service = CalculationServiceElectricityDemand()
        service.influx_connector = InfluxDBMock()
        service.init_calculation_service(self.energy_system)

        # # Execute
        ret_val = service.predict_demand({}, datetime(2020,1,14,0,0), TimeStepInformation(1,2), "25d212e5-ca5f-4a3d-9fb1-a5f024b2460a", self.energy_system)

        # Assert
        expected_active_power_profile = [108.0, 111.9999999999999, 108.0, 44.0, 52.0, 52.0, 48.0, 52.0, 52.0, 52.0, 52.0, 52.0, 52.0, 48.0, 52.0, 52.0, 52.0, 52.0, 60.0, 55.9999999999999, 84.0, 132.0, 124.0, 120.0, 115.9999999999999, 564.0, 508.0, 476.0, 516.0, 403.9999999999999, 60.0, 52.0, 48.0, 52.0, 48.0, 52.0, 52.0, 52.0, 48.0, 52.0, 52.0, 48.0, 108.0, 124.0, 120.0, 115.9999999999999, 115.9999999999999, 111.9999999999999]
        pf = 0.95
        expected_reactive_power_profile = [np.sqrt(1-pf**2)/pf * p for p in expected_active_power_profile]
        self.assertListEqual(expected_active_power_profile, ret_val["active_power"])
        self.assertListEqual(expected_reactive_power_profile, ret_val["reactive_power"])

if __name__ == '__main__':
    unittest.main()
