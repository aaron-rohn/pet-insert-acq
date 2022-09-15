from labjack import ljm

# Open first found LabJack
handle = ljm.openS("ANY", "ANY", "ANY")  # Any device, Any connection, Any identifier

# addresses, datatypes, operation, number of values, values
results = ljm.eAddresses(handle, 1,
        [1000], [ljm.constants.FLOAT32], [ljm.constants.WRITE], [1], [0 *  5.0])
print(results)

ljm.close(handle)
