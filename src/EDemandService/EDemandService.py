# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from esdl import esdl
import helics as h
from dots_infrastructure.DataClasses import EsdlId, HelicsCalculationInformation, PublicationDescription, TimeStepInformation
from dots_infrastructure.HelicsFederateHelpers import HelicsSimulationExecutor
from dots_infrastructure.Logger import LOGGER
from esdl import EnergySystem

import pandas as pd
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


    def init_calculation_service(self, energy_system: esdl.EnergySystem):
        # set windowsizes for different calculations
        self.window_size_in_seconds = 43200

        self.active_power_profiles: dict[EsdlId, list] = {}
        self.powerfactor: dict[EsdlId, float] = {}

        for esdl_id in self.simulator_configuration.esdl_ids:
            # Get profiles from the ESDL
            for obj in energy_system.eAllContents():
                if hasattr(obj, "id") and obj.id == esdl_id:
                    edemand_object = obj
                    profile = edemand_object.port[0].profile[0] # get profile from the first port
                    active_power_profile = []
                    active_power_profile_from_times = []
                    active_power_profile_to_times = []
                    for el in profile.element:
                        active_power_profile.append(el.value)
                        active_power_profile_from_times.append(el.from_)
                        active_power_profile_to_times.append(el.to)

                    power_profile = {
                        "from_times": active_power_profile_from_times,
                        "to_times": active_power_profile_to_times,
                        "active_power_profile": active_power_profile
                    }
                    power_profile_df = pd.DataFrame(power_profile)
                    power_profile_df.set_index("to_times", inplace=True)
                    self.active_power_profiles[esdl_id] = power_profile_df
                    self.powerfactor[esdl_id] = edemand_object.powerFactor

    def predict_demand(self, param_dict : dict, simulation_time : datetime, time_step_number : TimeStepInformation, esdl_id : EsdlId, energy_system : EnergySystem):

        assert (self.powerfactor[esdl_id] > 0.0) and (self.powerfactor[esdl_id] <= 1.0), "provide power factor between 0 and 1"
        predicted_active_power = self.active_power_profiles[esdl_id][simulation_time:simulation_time + timedelta(seconds=self.window_size_in_seconds)]["active_power_profile"].tolist()
        LOGGER.debug('predicted_active_power:', predicted_active_power)
        predicted_reactive_power = [self.calculate_Q_from_P_and_pf(active_power, self.powerfactor[esdl_id]) for active_power in
                                    predicted_active_power]
        LOGGER.debug('predicted_reactive_power:', predicted_reactive_power)

        ret_val = {}
        ret_val["active_power"] = predicted_active_power
        ret_val["reactive_power"] = predicted_reactive_power
        return ret_val

    @staticmethod
    def calculate_Q_from_P_and_pf(P, pf):
        return np.sqrt(1-pf**2)/pf * P


if __name__ == "__main__":

    helics_simulation_executor = CalculationServiceElectricityDemand()
    helics_simulation_executor.start_simulation()
    helics_simulation_executor.stop_simulation()
