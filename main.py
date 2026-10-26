import time
from communication_library.communication_manager import CommunicationManager, TransportType
from communication_library.tcp_transport import TcpSettings
from communication_library.frame import Frame
from communication_library import ids
from communication_library.exceptions import TransportTimeoutError, UnregisteredCallbackError

rocket_state = {
    'fuel_level': 0.0,
    'oxidizer_level': 0.0,
    'altitude': 0.0,
    'oxidizer_pressure': 0.0
}


def send_servo_command(cm: CommunicationManager, device_id: int, position: int) -> None:
    """Dispatch a servo control command frame."""
    frame = Frame(
        destination=ids.BoardID.ROCKET,
        priority=ids.PriorityID.LOW,
        action=ids.ActionID.SERVICE,
        source=ids.BoardID.SOFTWARE,
        device_type=ids.DeviceID.SERVO,
        device_id=device_id,
        data_type=ids.DataTypeID.INT16,
        operation=ids.OperationID.SERVO.value.POSITION,
        payload=(position,)
    )
    cm.push(frame)
    cm.send()


def send_relay_command(cm: CommunicationManager, device_id: int, open_relay: bool) -> None:
    """Dispatch a relay control command frame."""
    op = ids.OperationID.RELAY.value.OPEN if open_relay else ids.OperationID.RELAY.value.CLOSE
    frame = Frame(
        destination=ids.BoardID.ROCKET,
        priority=ids.PriorityID.LOW,
        action=ids.ActionID.SERVICE,
        source=ids.BoardID.SOFTWARE,
        device_type=ids.DeviceID.RELAY,
        device_id=device_id,
        data_type=ids.DataTypeID.NO_DATA,
        operation=op,
        payload=()
    )
    cm.push(frame)
    cm.send()


if __name__ == "__main__":
    cm = CommunicationManager()
    cm.change_transport_type(TransportType.TCP)

    print("Connecting to simulator proxy interface...")
    cm.connect(TcpSettings("127.0.0.1", 3000))
    print("Connection established. Starting launch sequence...\n")

    current_phase = "INIT_WAIT"
    init_timer = time.time()
    last_print_time = 0.0
    max_altitude = 0.0

    while True:
        try:
            frame = cm.receive()
        except TransportTimeoutError:
            current_time = time.time()
            alt = rocket_state['altitude']

            # Track peak altitude for apogee detection
            if alt > max_altitude:
                max_altitude = alt

            # Log status every 2 seconds
            if current_time - last_print_time > 2.0:
                print(f"[STATUS] Phase: {current_phase} | Oxidizer: {rocket_state['oxidizer_level']:.1f}% | "
                      f"Fuel: {rocket_state['fuel_level']:.1f}% | Pressure: {rocket_state['oxidizer_pressure']:.1f} bar | Altitude: {alt:.1f}m")
                last_print_time = current_time

            # Phase 1: Wait and open oxidizer valve (ID: 1)
            if current_phase == "INIT_WAIT" and current_time - init_timer > 2.0:
                print("\n[FSM] Phase 1: Oxidizer tanking started.")
                send_servo_command(cm, device_id=1, position=0)
                current_phase = "WAITING_FOR_OXIDIZER"

            # Phase 2: Wait for 100% oxidizer -> close valve and start fuel tanking
            elif current_phase == "WAITING_FOR_OXIDIZER":
                if rocket_state['oxidizer_level'] >= 100.0:
                    print("\n[FSM] Phase 2: Oxidizer ready. Closing valve and starting fuel tanking.")
                    send_servo_command(cm, device_id=1, position=100)
                    send_servo_command(cm, device_id=0, position=0)
                    current_phase = "WAITING_FOR_FUEL"

            # Phase 3: Wait for 100% fuel -> close valve and turn on heater (ID: 0)
            elif current_phase == "WAITING_FOR_FUEL":
                if rocket_state['fuel_level'] >= 100.0:
                    print("\n[FSM] Phase 3: Fuel ready. Closing valve and turning on heater.")
                    send_servo_command(cm, device_id=0, position=100)
                    send_relay_command(cm, device_id=0, open_relay=True)
                    current_phase = "HEATING_OXIDIZER"

            # Phase 4: Wait for pressure within 55-65 bar range
            elif current_phase == "HEATING_OXIDIZER":
                pressure = rocket_state['oxidizer_pressure']
                if 55.0 <= pressure <= 65.0:
                    print(f"\n[FSM] Phase 4: Pressure nominal ({pressure:.1f} bar). Ignition sequence.")

                    # Turn off heater
                    send_relay_command(cm, device_id=0, open_relay=False)

                    # Open main propellant valves: fuel (ID: 2) and oxidizer (ID: 3)
                    send_servo_command(cm, device_id=2, position=0)
                    send_servo_command(cm, device_id=3, position=0)

                    # Trigger ignition relay (ID: 1)
                    time.sleep(0.2)
                    send_relay_command(cm, device_id=1, open_relay=True)

                    current_phase = "FLIGHT"
                    print("[FSM] ROCKET LIFTOFF.")

            # Phase 5: Flight and apogee detection
            elif current_phase == "FLIGHT":
                if rocket_state['fuel_level'] <= 0.0:
                    if alt < max_altitude - 2.0:
                        print(f"\n[FSM] Phase 5: Apogee reached ({max_altitude:.1f}m). Deploying parachute.")
                        send_relay_command(cm, device_id=2, open_relay=True)
                        current_phase = "DESCENDING"

            # Phase 6: Descent and touchdown detection
            elif current_phase == "DESCENDING":
                if alt <= 5.0:
                    print("\n" + "=" * 50)
                    print(f"[SUCCESS] MISSION SUCCESSFUL. Landing detected - last measured altitude: {alt:.1f}m.")
                    print("=" * 50)
                    break

            continue

        except UnregisteredCallbackError as e:
            f = e.frame
            if f.action == ids.ActionID.FEED and f.device_type == ids.DeviceID.SENSOR:
                sensor_map = {0: 'fuel_level', 1: 'oxidizer_level', 2: 'altitude', 3: 'oxidizer_pressure'}
                if f.device_id in sensor_map:
                    rocket_state[sensor_map[f.device_id]] = float(f.data)

    cm.disconnect()