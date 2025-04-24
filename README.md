# Calculation service for esdl_type ElectricityDemand:

This calculation service publishes values for an electricity demand profile. The values of the profile should be specified in the ESDL file.

## Calculations

### predict demand 

Send the values of the electricity demand profile for the coming 12 hours.
#### Output values
|Name             |data_type             |unit             |description             |
|-----------------|----------------------|-----------------|------------------------|
|active_power|VECTOR|W|The active power demand as vector of floats for the next 12 hours in watts.|
|reactive_power|VECTOR|W|The reactive power demand as vector of floats for the next 12 hours in watts.|

### Relevant links
|Link             |description             |
|-----------------|------------------------|
|[Electricity Demand ESDL Type](https://energytransition.github.io/#router/doc-content/687474703a2f2f7777772e746e6f2e6e6c2f6573646c/ElectricityDemand.html)|Details on the electricity demand esdl type|
