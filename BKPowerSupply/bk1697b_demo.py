import serial
import time

# Update this with the correct serial port found in the previous step
# command to find port: ` dmesg | tail`
SERIAL_PORT = '/dev/ttyACM0' 
# Check your device manual for the correct baud rate. A common value is 9600.
#BAUD_RATE = 115200
BAUD_RATE = 9600

## Make sure enable the SCPI feature first: shift/clear, then 4, then select Y using rotary knob 

def main():
    """Communicates with the BK 1697B power supply."""
    try:
        # Initialize the serial connection
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1  # Set a timeout for read operations
        )

        print(f"Connecting to {ser.name}...")
        
        # Give the connection a moment to establish
        time.sleep(2) 

        if ser.is_open:
            print("Serial port is open.")
            
            # --- Example: Read the power supply's IDN string ---
            # SCPI command for query is typically "*IDN?".
            # The command must be encoded to bytes before sending.
            idn_command = b'*IDN?\n'
            ser.write(idn_command)
            time.sleep(0.5) # Wait for the response
            
            # Read the response. readline() reads until a newline character.
            idn_response = ser.readline()
            
            # Decode the response from bytes to a human-readable string.
            if idn_response:
                print(f"Received IDN: {idn_response.decode('utf-8').strip()}")
            else:
                print("Failed to read IDN!")


            # Read SCPI version
            sysinfo_command = b'SYST:VER?\n'
            #sysinfo_command = b'SYST:SN?\n' ## serial number
            ser.write(sysinfo_command)
            time.sleep(0.5) # Wait for the response
            
            # Read the response. readline() reads until a newline character.
            sysinfo_response = ser.readline()
            
            # Decode the response from bytes to a human-readable string.
            if sysinfo_response:
                print(f"Received SCPI veresion: {sysinfo_response.decode('utf-8').strip()}")
            else:
                print("Failed to read SCPI version!")
            

            # --- Example: Set the voltage (replace with actual command) ---
            # NOTE: The following is a placeholder. Refer to your BK 1697B manual for the correct command.
            # An example SCPI command might be "VOLT 5.0".
            setVolt_value = 9
            #set_voltage_command = b'VOLT 10.00V\n'
            #set_voltage_command = "VOLT {:.2f}V\n".format(setVolt_value).encode()
            set_voltage_command = f"VOLT {setVolt_value:.2f}V\n".encode()

            #print(f"voltage setting command {set_voltage_command}")
            ser.write(set_voltage_command)
            print("Sent command to set voltage.")
            
            # --- Example: Read the current voltage setting (replace with actual command) ---
            # NOTE: The following is a placeholder. Refer to your BK 1697B manual for the correct query command.
            get_voltage_command = b'VOLT?\n'
            ser.write(get_voltage_command)
            time.sleep(0.5)
            voltage_response = ser.readline()
            if voltage_response:
                print(f"Current voltage setting: {voltage_response.decode('utf-8').strip()}")
            else:
                print("Failed to read voltage setting!")
            
            ## read whether the output is ON or not
            get_output_command = b'OUTP?\n'
            ser.write(get_output_command)
            time.sleep(0.5)
            output_response = ser.readline()
            if output_response:
                output_result = output_response.decode('utf-8').strip()
                print(f"output ON/OFF result {output_result}", type(output_result))
                if int(output_result) == 1:
                    print("Attempt to enable the output!!! ")
                    enable_output_command = b'OUTP 0\n'
                    ser.write(enable_output_command)
                    time.sleep(0.5)
                    ser.write(get_output_command)
                    time.sleep(0.5)
                    output_response = ser.readline()
                    print(f"output ON/OFF result: {output_response.decode('utf-8').strip()}")
                    time.sleep(1.0)## allow voltage to ramp up 

            else:
                print("failed to read the output ON/OFF ")

            ## read the output voltage 
            get_measvoltage_command = b'MEAS:VOLT?\n'
            ser.write(get_measvoltage_command)
            time.sleep(0.5)
            measvoltage_response = ser.readline()
            if measvoltage_response:
                print(f"Measured voltage setting: {measvoltage_response.decode('utf-8').strip()}")
            else:
                print("Failed to read measured voltage!")
        
        else:
            print("Could not open serial port.")

    except serial.SerialException as e:
        print(f"Error: {e}")

    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == "__main__":
    main()
