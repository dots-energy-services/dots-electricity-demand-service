from datetime import datetime
from pathlib import Path
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
    return SimulatorConfiguration("ElectricityDemand", ["138a4b7f-b8ee-4655-a6c2-76947e9b8f7a"], "Mock-Econnection", "127.0.0.1", BROKER_TEST_PORT, "test-id", SIMULATION_DURATION_IN_SECONDS, START_DATE_TIME, "test-host", "test-port", "test-username", "test-password", "test-database-name", h.HelicsLogLevel.DEBUG, ["PVInstallation", "EConnection"])

class Test(unittest.TestCase):

    def setUp(self):
        CalculationServiceHelperFunctions.get_simulator_configuration_from_environment = simulator_environment_e_demand
        esh = EnergySystemHandler()
        esh.load_file(str(Path(__file__).parent /"test.esdl"))
        self.energy_system = esh.get_energy_system()

    def test_predict_demand(self):

        # Arrange
        service = CalculationServiceElectricityDemand()
        service.influx_connector = InfluxDBMock()
        service.init_calculation_service(self.energy_system)

        # # Execute
        ret_val = service.predict_demand({}, datetime(2020,1,1,0,15), TimeStepInformation(1,2), "138a4b7f-b8ee-4655-a6c2-76947e9b8f7a", self.energy_system)

        # Assert
        expected_active_power_profile = [0.171986486, 0.079993714, 0.067994657, 0.123990257, 0.187985229, 0.203983972, 0.183985543, 0.287977372, 0.187985229, 0.191984915, 0.215983029, 0.159987429, 0.067994657, 0.075994029, 0.147988372, 0.099992143, 0.063994972, 0.095992457, 0.155987743, 0.1679868, 0.191984915, 0.247980515, 0.231981772, 0.211983343, 2.20782652, 2.075836891, 0.195984601, 0.315975172, 0.255979886, 0.335973601, 0.159987429, 0.147988372, 0.195984601, 0.391969201, 0.335973601, 0.343972972, 0.463963544, 0.459963858, 0.379970144, 0.307975801, 0.295976744, 0.52395883, 0.651948773, 0.391969201, 0.291977058, 0.671947202, 1.427887804, 1.083914831]
        expected_active_power_profile = [val * 1000 for val in expected_active_power_profile]

        pf = 0.95
        expected_reactive_power_profile = [np.sqrt(1-pf**2)/pf * p for p in expected_active_power_profile]
        self.assertListEqual(expected_active_power_profile, ret_val["active_power"])
        self.assertListEqual(expected_reactive_power_profile, ret_val["reactive_power"])

    def test_current_demand(self):

        # Arrange
        service = CalculationServiceElectricityDemand()
        service.influx_connector = InfluxDBMock()
        service.init_calculation_service(self.energy_system)

        # # Execute
        ret_val = service.current_demand({}, datetime(2020,1,1,0,15), TimeStepInformation(1,2), "138a4b7f-b8ee-4655-a6c2-76947e9b8f7a", self.energy_system)

        # Assert
        expected_active_power = 0.171986486 * 1000
        pf = 0.95
        expected_reactive_power_profile = np.sqrt(1-pf**2)/pf * expected_active_power
        self.assertEqual(expected_active_power, ret_val["current_active_power"])
        self.assertEqual(expected_reactive_power_profile, ret_val["current_reactive_power"])

if __name__ == '__main__':
    unittest.main()
