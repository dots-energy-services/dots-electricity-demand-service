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
    return SimulatorConfiguration("ElectricityDemand", ["7c2c8aed-63f3-417e-b413-195032a9072a"], "Mock-Econnection", "127.0.0.1", BROKER_TEST_PORT, "test-id", SIMULATION_DURATION_IN_SECONDS, START_DATE_TIME, "test-host", "test-port", "test-username", "test-password", "test-database-name", h.HelicsLogLevel.DEBUG, ["PVInstallation", "EConnection"])

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
        ret_val = service.predict_demand({}, datetime(2020,1,14,0,15), TimeStepInformation(1,2), "7c2c8aed-63f3-417e-b413-195032a9072a", self.energy_system)

        # Assert
        expected_active_power_profile = [336.0, 1888.0, 144.0, 136.0, 136.0, 132.0, 180.0, 160.0, 111.9999999999999, 111.9999999999999, 111.9999999999999, 111.9999999999999, 111.9999999999999, 111.9999999999999, 160.0, 152.0, 111.9999999999999, 111.9999999999999, 111.9999999999999, 111.9999999999999, 111.9999999999999, 108.0, 156.0, 160.0, 111.9999999999999, 111.9999999999999, 111.9999999999999, 111.9999999999999, 111.9999999999999, 111.9999999999999, 124.0, 180.0, 248.0, 252.0, 304.0, 256.0, 1064.0, 860.0, 440.0, 364.0, 288.0, 1188.0, 2664.0, 2152.0, 2080.0, 1460.0, 580.0, 192.0 ]
        pf = 0.95
        expected_reactive_power_profile = [np.sqrt(1-pf**2)/pf * p for p in expected_active_power_profile]
        self.assertListEqual(expected_active_power_profile, ret_val["active_power"])
        self.assertListEqual(expected_reactive_power_profile, ret_val["reactive_power"])

if __name__ == '__main__':
    unittest.main()
