# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dataclasses import dataclass
from dots_infrastructure.EsdlProfileParsingClasses import ParsedDateTimeProfile, ParsedStaticProfile, ParsedTimeSeriesProfile
from esdl import DateTimeProfile, MultiplierEnum, QuantityAndUnitType, TimeSeriesProfile, esdl
import helics as h
from dots_infrastructure.DataClasses import EsdlId, HelicsCalculationInformation, PublicationDescription, TimeStepInformation
from dots_infrastructure.HelicsFederateHelpers import HelicsSimulationExecutor
from dots_infrastructure.Logger import LOGGER
from esdl import EnergySystem

import numpy as np

@dataclass
class ProfileMetaData:
    profile : ParsedStaticProfile
    unit : QuantityAndUnitType


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

        publication_values_current_demand = [
            PublicationDescription(global_flag=True, 
                                   esdl_type="ElectricityDemand",
                                   output_name="current_active_power",
                                   output_unit="W", 
                                   data_type=h.HelicsDataType.DOUBLE),
            PublicationDescription(global_flag=True,
                                   esdl_type="ElectricityDemand",
                                   output_name="current_reactive_power",
                                   output_unit="VAr",
                                   data_type=h.HelicsDataType.DOUBLE)
        ]

        calculation_information_current_demand = HelicsCalculationInformation(
            time_period_in_seconds=edemand_period_in_seconds,
            offset=0, 
            uninterruptible=False, 
            wait_for_current_time_update=False, 
            terminate_on_error=True, 
            calculation_name="current_demand",
            inputs=[],
            outputs=publication_values_current_demand, 
            calculation_function=self.current_demand
        )
        self.add_calculation(calculation_information_current_demand)


    def init_calculation_service(self, energy_system: esdl.EnergySystem):
        # set windowsizes for different calculations
        self.window_size_in_seconds = 43200
        self.current_demand_period_seconds = 900

        self.active_power_profiles: dict[EsdlId, ProfileMetaData] = {}
        self.powerfactor: dict[EsdlId, float] = {}
        for obj in energy_system.eAllContents():
            if hasattr(obj, "id") and obj.id in self.simulator_configuration.esdl_ids:
                esdl_id = obj.id
                edemand_object = obj
                profile_port = next(port for port in edemand_object.port if len(port.profile) > 0)
                profile = profile_port.profile[0]
                if isinstance(profile, DateTimeProfile):
                    parsed_profile = ParsedDateTimeProfile(profile)
                elif isinstance(profile, TimeSeriesProfile):
                    parsed_profile = ParsedTimeSeriesProfile(profile)

                self.active_power_profiles[obj.id] = ProfileMetaData(parsed_profile, profile.profileQuantityAndUnit)

                self.powerfactor[esdl_id] = edemand_object.powerFactor

    def predict_demand(self, param_dict : dict, simulation_time : datetime, time_step_number : TimeStepInformation, esdl_id : EsdlId, energy_system : EnergySystem):

        assert (self.powerfactor[esdl_id] > 0.0) and (self.powerfactor[esdl_id] <= 1.0), "provide power factor between 0 and 1"
        from_date = simulation_time
        to_date = simulation_time + timedelta(seconds=self.window_size_in_seconds - 1)
        profile_meta_data = self.active_power_profiles[esdl_id]
        predicted_active_power = profile_meta_data.profile.get_data(from_date, to_date)
        if profile_meta_data.unit.multiplier == MultiplierEnum.from_string('KILO'):
            predicted_active_power = [1000 * val for val in predicted_active_power]

        LOGGER.debug(f'simulation_time: {simulation_time}' )
        LOGGER.debug(f'predicted_active_power: {predicted_active_power}' )
        predicted_reactive_power = [self.calculate_Q_from_P_and_pf(active_power, self.powerfactor[esdl_id]) for active_power in
                                    predicted_active_power]
        LOGGER.debug(f'predicted_reactive_power: {predicted_reactive_power}')

        ret_val = {}
        ret_val["active_power"] = predicted_active_power
        ret_val["reactive_power"] = predicted_reactive_power
        return ret_val
    
    def current_demand(self, param_dict : dict, simulation_time : datetime, time_step_number : TimeStepInformation, esdl_id : EsdlId, energy_system : EnergySystem):
        assert (self.powerfactor[esdl_id] > 0.0) and (self.powerfactor[esdl_id] <= 1.0), "provide power factor between 0 and 1"
        from_date = simulation_time
        to_date = simulation_time + timedelta(seconds=self.current_demand_period_seconds - 1)
        profile_meta_data = self.active_power_profiles[esdl_id]
        active_power = profile_meta_data.profile.get_data(from_date, to_date)[0]
        if profile_meta_data.unit.multiplier == MultiplierEnum.from_string('KILO'):
            active_power = 1000 * active_power

        reactive_power = self.calculate_Q_from_P_and_pf(active_power, self.powerfactor[esdl_id])
        ret_val = {}
        ret_val["current_active_power"] = active_power
        ret_val["current_reactive_power"] = reactive_power
        self.influx_connector.set_time_step_data_point(esdl_id, "current_active_power", simulation_time, active_power)
        self.influx_connector.set_time_step_data_point(esdl_id, "current_reactive_power", simulation_time, reactive_power)
        return ret_val

    @staticmethod
    def calculate_Q_from_P_and_pf(P, pf):
        return np.sqrt(1-pf**2)/pf * P


if __name__ == "__main__":

    helics_simulation_executor = CalculationServiceElectricityDemand()
    helics_simulation_executor.start_simulation()
    helics_simulation_executor.stop_simulation()
