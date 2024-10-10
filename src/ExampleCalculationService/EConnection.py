# -*- coding: utf-8 -*-
from datetime import datetime
from esdl import esdl
import helics as h
from dots_infrastructure.DataClasses import EsdlId, HelicsCalculationInformation, PublicationDescription, SubscriptionDescription, TimeStepInformation, TimeRequestType
from dots_infrastructure.HelicsFederateHelpers import HelicsSimulationExecutor
from dots_infrastructure.Logger import LOGGER
from esdl import EnergySystem

import numpy as np

class CalculationServiceElectricityDemand(HelicsSimulationExecutor):

    def __init__(self):
        super().__init__()

        publication_values = [
            PublicationDescription(global_flag=True, 
                                   esdl_type="ElectricityDemand",
                                   output_name="active_power",
                                   output_unit="W", 
                                   data_type=h.HelicsDataType.VECTOR),
            PublicationDescription(global_flag=True,
                                   esdl_type="ElectricityDemand",
                                   output_name="reactive_power",
                                   output_unit="VAr",
                                   data_type=h.HelicsDataType.VECTOR)
        ]

        edemand_period_in_seconds = 900

        calculation_information = HelicsCalculationInformation(
            time_period_in_seconds=edemand_period_in_seconds,
            offset=0, 
            uninterruptible=False, 
            wait_for_current_time_update=False, 
            terminate_on_error=True, 
            calculation_name="predict_demand",
            inputs=[],
            outputs=publication_values, 
            calculation_function=self.predict_demand
        )
        self.add_calculation(calculation_information)

        publication_values = [
            PublicationDescription(True, "ElectricityDemand", "active_power_up_to_next_day", "W", h.HelicsDataType.VECTOR),
            PublicationDescription(True, "ElectricityDemand", "reactive_power_up_to_next_day", "VAr",
                                   h.HelicsDataType.VECTOR),
        ]

        edemand_up_to_next_day_period_in_seconds = 900

        calculation_information_schedule = HelicsCalculationInformation(edemand_up_to_next_day_period_in_seconds, 0, False, False, True, "predict_demand_up_to_next_day", [], publication_values, self.predict_demand_up_to_next_day)
        self.add_calculation(calculation_information_schedule)

    def init_calculation_service(self, energy_system: esdl.EnergySystem):
        LOGGER.info("init calculation service")
        # set windowsizes for different calculations
        self.window_size = 48
        self.window_size_up_to_next_day = 144

        self.active_power_profiles: dict[EsdlId, list] = {}
        self.powerfactor: dict[EsdlId, float] = {}

        for esdl_id in self.simulator_configuration.esdl_ids:
            LOGGER.info(f"Example of iterating over esdl ids: {esdl_id}")
            # Get profiles from the ESDL
            for obj in energy_system.eAllContents():
                if hasattr(obj, "id") and obj.id == esdl_id:
                    edemand_object = obj
                    profile = edemand_object.port[0].profile[0] # get profile from the first port
                    # print(profile)
                    active_power_profile = []
                    for el in profile.element:
                        active_power_profile.append(el.value)
                    self.active_power_profiles[esdl_id] = active_power_profile
                    self.powerfactor[esdl_id] = edemand_object.powerFactor
                    # print(edemand_object.powerFactor)

    def predict_demand(self, param_dict : dict, simulation_time : datetime, time_step_number : TimeStepInformation, esdl_id : EsdlId, energy_system : EnergySystem):
        LOGGER.info("calculation 'predict_demand' started")
        time_step_nr = time_step_number.current_time_step_number
        assert (self.powerfactor[esdl_id] > 0.0) and (self.powerfactor[esdl_id] <= 1.0), "provide power factor between 0 and 1"
        predicted_active_power = self.active_power_profiles[esdl_id][
                                      time_step_nr - 1:time_step_nr - 1 + self.window_size]
        print('predicted_active_power:', predicted_active_power)
        predicted_reactive_power = [self.calculate_Q_from_P_and_pf(active_power, self.powerfactor[esdl_id]) for active_power in
                                    predicted_active_power]
        print('predicted_reactive_power:', predicted_reactive_power)

        LOGGER.info("calculation 'predict_demand' finished")
        # END user calc

        # return a list for all outputs:
        ret_val = {}
        ret_val["active_power"] = predicted_active_power
        ret_val["reactive_power"] = predicted_reactive_power
        # self.influx_connector.set_time_step_data_point(esdl_id, "EConnectionDispatch", simulation_time, ret_val["EConnectionDispatch"])
        return ret_val
    
    def predict_demand_up_to_next_day(self, param_dict : dict, simulation_time : datetime, time_step_number : TimeStepInformation, esdl_id : EsdlId, energy_system : EnergySystem):
        # START user calc
        LOGGER.info("calculation 'predict_demand_up_to_next_day' started")
        time_step_nr = time_step_number.current_time_step_number
        hour_of_day = simulation_time.hour
        minute_of_hour = simulation_time.minute

        # Output non-empty lists at 12:00
        if hour_of_day == 12 and minute_of_hour == 0.0:
            assert (self.powerfactor[esdl_id] > 0.0) and (
                        self.powerfactor[esdl_id] <= 1.0), "provide power factor between 0 and 1"
            LOGGER.debug(f"window size: {self.window_size_up_to_next_day}")
            predicted_active_power = self.active_power_profiles[esdl_id][
                                     time_step_nr - 1:time_step_nr - 1 + self.window_size_up_to_next_day]
            LOGGER.debug(f"Length predicted output: {len(predicted_active_power)}")
            predicted_reactive_power = [self.calculate_Q_from_P_and_pf(active_power, self.powerfactor[esdl_id]) for
                                        active_power in
                                        predicted_active_power]
        else:
            predicted_active_power = []
            predicted_reactive_power = []
        LOGGER.info("calculation 'predict_demand_up_to_next_day' finished")
        # END user calc
        # return a list for all outputs:
        ret_val = {}
        ret_val["active_power_up_to_next_day"] = predicted_active_power
        ret_val["reactive_power_up_to_next_day"]  = predicted_reactive_power
        return ret_val

    @staticmethod
    def calculate_Q_from_P_and_pf(P, pf):
        return np.sqrt(1-pf**2)/pf * P


if __name__ == "__main__":

    helics_simulation_executor = CalculationServiceElectricityDemand()
    helics_simulation_executor.start_simulation()
    helics_simulation_executor.stop_simulation()
