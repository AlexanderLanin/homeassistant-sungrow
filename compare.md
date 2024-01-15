# Summary:

| Host | Mode | Read Calls | Result | Errors |
| --- | --- | --- | --- | --- |
| 192.168.13.79/1 | pymodbus | 22 | 1219 registers retrieved | 0 registers not supported |
| 192.168.13.79/None | winet_http | None | Failed | CannotConnectError:  |
| 192.168.13.58/1 | pymodbus | 270 | 379 registers retrieved | 136 registers not supported |
| 192.168.13.58/None | winet_http | 24 | 1123 registers retrieved | 1 registers not supported |
| 192.168.13.80/2 | pymodbus | 22 | 1219 registers retrieved | 0 registers not supported |
| 192.168.13.80/None | winet_http | None | Failed | CannotConnectError:  |
| 192.168.13.74/1 | pymodbus | 270 | 379 registers retrieved | 136 registers not supported |
| 192.168.13.74/None | winet_http | None | Failed | CannotConnectError:  |


# A2350415770
| Signal | pymodbus/192.168.13.79/1 | pymodbus/192.168.13.58/1 | winet_http/192.168.13.58/None | 
| --- | --- | --- | --- |
| protocol_number | 1094856704 | 1094791472 | 1094856704 | 
| protocol_version | 16781568 | 16778496 | 16781568 | 
| arm_software_version | 16722 | 16722 | 16722 | 
| dsp_software_version | 19780 | 19780 | 19780 | 
| serial_number | A2350415770 | A2350415770 | A2350415770 | 
| device_type_code | SH8.0RT-20 | SH8.0RT-20 | SH8.0RT-20 | 
| nominal_output_power | 8.0 | 8.0 | 8.0 | 
| output_type | 3P4L | 3P4L | 3P4L | 
| daily_output_energy_pv_and_battery | 0.0 | 0.0 | 0.0 | 
| total_output_energy_pv_and_battery | 125.2 | 125.2 | 125.2 | 
| total_running_time | None | 0 | None | 
| internal_temperature | 33.9 | 34.0 | 33.9 | 
| total_apparent_power | 145 | 0 | 78 | 
| mppt_1_voltage | 0.0 | 0.0 | 0.0 | 
| mppt_1_current | 0.0 | 0.0 | 0.0 | 
| mppt_2_voltage | 0.0 | 0.0 | 0.0 | 
| mppt_2_current | 0.0 | 0.0 | 0.0 | 
| mppt_3_voltage | None | 0.0 | None | 
| mppt_3_current | None | 0.0 | None | 
| total_dc_power | 0 | 0 | 0 | 
| phase_a_voltage | 231.1 | 231.0 | 231.2 | 
| phase_b_voltage | 232.6 | 232.7 | 232.5 | 
| phase_c_voltage | 232.2 | 232.3 | 232.6 | 
| phase_a_current | 0.0 | 0.0 | 0.0 | 
| phase_b_current | 0.0 | 0.0 | 0.0 | 
| phase_c_current | 0.0 | 0.0 | 0.0 | 
| total_active_power | 0 | 0 | 0 | 
| total_reactive_power | 81 | -2 | -2 | 
| power_factor | -0.69 | 1.0 | 1.0 | 
| grid_frequency | 50.0 | 500.2 | 49.9 | 
| work_state_1 | None | 0 | None | 
| alarm_time_year | None | 0 | None | 
| alarm_time_month | None | 0 | None | 
| alarm_time_day | None | 0 | None | 
| alarm_time_hour | None | 0 | None | 
| alarm_time_minute | None | 0 | None | 
| alarm_time_second | None | 0 | None | 
| alarm_code_1 | None | 0 | None | 
| nominal_reactive_power | 4800.0 | 0.0 | 4800.0 | 
| array_insulation_resistance | 748 | None | 748 | 
| active_power_regulation_setpoint | None | None | None | 
| reactive_power_regulation_setpoint | -1 | None | -1 | 
| work_state_2 | None | None | None | 
| meter_power | -1 | None | -1 | 
| meter_a_phase_power | -1 | None | -1 | 
| meter_b_phase_power | 5373951 | None | 5177343 | 
| meter_c_phase_power | -65536 | None | -65536 | 
| meter_load_power | -1 | None | -1 | 
| daily_export_energy | None | None | None | 
| total_export_energy | None | None | None | 
| daily_import_energy | None | None | None | 
| total_import_energy | None | None | None | 
| daily_direct_energy_consumption | None | None | None | 
| total_direct_energy_consumption | None | None | None | 
| daily_running_time | None | None | None | 
| mppt_4_voltage | None | None | None | 
| mppt_4_current | None | None | None | 
| mppt_5_voltage | None | None | None | 
| mppt_5_current | None | None | None | 
| mppt_6_voltage | None | None | None | 
| mppt_6_current | None | None | None | 
| mppt_7_voltage | None | None | None | 
| mppt_7_current | None | None | None | 
| mppt_8_voltage | None | None | None | 
| mppt_8_current | None | None | None | 
| monthly_power_yields | None | None | None | 
| mppt_9_voltage | None | None | None | 
| mppt_9_current | None | None | None | 
| mppt_10_voltage | None | None | None | 
| mppt_10_current | None | None | None | 
| mppt_11_voltage | None | None | None | 
| mppt_11_current | None | None | None | 
| mppt_12_voltage | None | None | None | 
| mppt_12_current | None | None | None | 
| total_power_yields | None | None | None | 
| negative_voltage_to_the_ground | -0.1 | None | -0.1 | 
| bus_voltage | 626.0 | None | 626.0 | 
| grid_frequency_ | 50.03 | None | 49.98 | 
| pid_work_state | None | None | None | 
| pid_alarm_code | None | None | None | 
| export_power | -434 | None | -388 | 
| meter_active_power | 408 | 421 | 389 | 
| meter_active_power_phase_a | 654 | 659 | 667 | 
| meter_active_power_phase_b | -667 | -650 | -698 | 
| meter_active_power_phase_c | 421 | 412 | 420 | 
| power_meter | 434 | None | 388 | 
| export_limit_min | 0.0 | 0.0 | 0.0 | 
| export_limit_max | 16000.0 | 16000.0 | 16000.0 | 
| bdc_rated_power | 8000.0 | 8000.0 | 8000.0 | 
| bms_max_charging_current | 30 | 30 | 30 | 
| bms_max_discharging_current | 27 | 27 | 27 | 
| battery_capacity_high_precision | 9.6 | 0.0 | 9.6 | 
| backup_power_phase_a | -25 | None | -25 | 
| backup_power_phase_b | -31 | None | -31 | 
| backup_power_phase_c | -31 | None | -31 | 
| backup_power_total | -87 | None | -87 | 
| pv_power_of_today | {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0, 17: 0, 18: 0, 19: 0, 20: 0, 21: 0, 22: 0, 23: 0, 24: 0, 25: 0, 26: 0, 27: 0, 28: 0, 29: 0, 30: 0, 31: 0, 32: 0, 33: 0, 34: 0, 35: 0, 36: 0, 37: 0, 38: 0, 39: 0, 40: 0, 41: 0, 42: 0, 43: 0, 44: 0, 45: 0, 46: 0, 47: 0, 48: 0, 49: 0, 50: 0, 51: 0, 52: 0, 53: 0, 54: 0, 55: 0, 56: 0, 57: 0, 58: 0, 59: 0, 60: 0, 61: 0, 62: 0, 63: 0, 64: 0, 65: 0, 66: 0, 67: 0, 68: 0, 69: 0, 70: 0, 71: 0, 72: 0, 73: 0, 74: 0, 75: 0, 76: 0, 77: 0, 78: 0, 79: 0, 80: 0, 81: 0, 82: 0, 83: 0, 84: 0, 85: 0, 86: 0, 87: 0, 88: 0, 89: 0, 90: 0, 91: 0, 92: 0, 93: 0, 94: 0, 95: 0} | None | {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0, 17: 0, 18: 0, 19: 0, 20: 0, 21: 0, 22: 0, 23: 0, 24: 0, 25: 0, 26: 0, 27: 0, 28: 0, 29: 0, 30: 0, 31: 0, 32: 0, 33: 0, 34: 0, 35: 0, 36: 0, 37: 0, 38: 0, 39: 0, 40: 0, 41: 0, 42: 0, 43: 0, 44: 0, 45: 0, 46: 0, 47: 0, 48: 0, 49: 0, 50: 0, 51: 0, 52: 0, 53: 0, 54: 0, 55: 0, 56: 0, 57: 0, 58: 0, 59: 0, 60: 0, 61: 0, 62: 0, 63: 0, 64: 0, 65: 0, 66: 0, 67: 0, 68: 0, 69: 0, 70: 0, 71: 0, 72: 0, 73: 0, 74: 0, 75: 0, 76: 0, 77: 0, 78: 0, 79: 0, 80: 0, 81: 0, 82: 0, 83: 0, 84: 0, 85: 0, 86: 0, 87: 0, 88: 0, 89: 0, 90: 0, 91: 0, 92: 0, 93: 0, 94: 0, 95: 0} | 
| pv_energy_yields_daily | {0: 1.2, 1: 0.8, 2: 2.0, 3: 1.4, 4: 1.6, 5: 0.1, 6: 0.1, 7: 1.8, 8: 2.3, 9: 2.3, 10: 0.9, 11: 1.4, 12: 1.2, 13: 2.0, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0} | None | {0: 1.2, 1: 0.8, 2: 2.0, 3: 1.4, 4: 1.6, 5: 0.1, 6: 0.1, 7: 1.8, 8: 2.3, 9: 2.3, 10: 0.9, 11: 1.4, 12: 1.2, 13: 2.0, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0} | 
| pv_energy_yields_monthly | {0: 19.1, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | None | {0: 19.1, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | 
| pv_energy_yields_yearly_starting_2019 | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 18.4, 9: 19.1, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | None | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 18.4, 9: 19.1, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | 
| direct_power_consumption_from_pv_today | {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0, 17: 0, 18: 0, 19: 0, 20: 0, 21: 0, 22: 0, 23: 0, 24: 0, 25: 0, 26: 0, 27: 0, 28: 0, 29: 0, 30: 0, 31: 0, 32: 0, 33: 0, 34: 0, 35: 0, 36: 0, 37: 0, 38: 0, 39: 0, 40: 0, 41: 0, 42: 0, 43: 0, 44: 0, 45: 0, 46: 0, 47: 0, 48: 0, 49: 0, 50: 0, 51: 0, 52: 0, 53: 0, 54: 0, 55: 0, 56: 0, 57: 0, 58: 0, 59: 0, 60: 0, 61: 0, 62: 0, 63: 0, 64: 0, 65: 0, 66: 0, 67: 0, 68: 0, 69: 0, 70: 0, 71: 0, 72: 0, 73: 0, 74: 0, 75: 0, 76: 0, 77: 0, 78: 0, 79: 0, 80: 0, 81: 0, 82: 0, 83: 0, 84: 0, 85: 0, 86: 0, 87: 0, 88: 0, 89: 0, 90: 0, 91: 0, 92: 0, 93: 0, 94: 0, 95: 0} | None | {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0, 17: 0, 18: 0, 19: 0, 20: 0, 21: 0, 22: 0, 23: 0, 24: 0, 25: 0, 26: 0, 27: 0, 28: 0, 29: 0, 30: 0, 31: 0, 32: 0, 33: 0, 34: 0, 35: 0, 36: 0, 37: 0, 38: 0, 39: 0, 40: 0, 41: 0, 42: 0, 43: 0, 44: 0, 45: 0, 46: 0, 47: 0, 48: 0, 49: 0, 50: 0, 51: 0, 52: 0, 53: 0, 54: 0, 55: 0, 56: 0, 57: 0, 58: 0, 59: 0, 60: 0, 61: 0, 62: 0, 63: 0, 64: 0, 65: 0, 66: 0, 67: 0, 68: 0, 69: 0, 70: 0, 71: 0, 72: 0, 73: 0, 74: 0, 75: 0, 76: 0, 77: 0, 78: 0, 79: 0, 80: 0, 81: 0, 82: 0, 83: 0, 84: 0, 85: 0, 86: 0, 87: 0, 88: 0, 89: 0, 90: 0, 91: 0, 92: 0, 93: 0, 94: 0, 95: 0} | 
| direct_power_consumption_from_pv_daily | {0: 0.6, 1: 0.6, 2: 0.6, 3: 0.8, 4: 0.9, 5: 0.1, 6: 0.1, 7: 1.4, 8: 2.0, 9: 1.6, 10: 0.8, 11: 1.0, 12: 1.0, 13: 1.9, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0} | None | {0: 0.6, 1: 0.6, 2: 0.6, 3: 0.8, 4: 0.9, 5: 0.1, 6: 0.1, 7: 1.4, 8: 2.0, 9: 1.6, 10: 0.8, 11: 1.0, 12: 1.0, 13: 1.9, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0} | 
| direct_energy_consumption_from_pv_monthly | {0: 13.4, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | None | {0: 13.4, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | 
| direct_energy_consumption_from_pv_yearly_starting_2019 | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 6.3, 9: 13.4, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | None | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 6.3, 9: 13.4, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | 
| export_power_from_pv_today | {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0, 17: 0, 18: 0, 19: 0, 20: 0, 21: 0, 22: 0, 23: 0, 24: 0, 25: 0, 26: 0, 27: 0, 28: 0, 29: 0, 30: 0, 31: 0, 32: 0, 33: 0, 34: 0, 35: 0, 36: 0, 37: 0, 38: 0, 39: 0, 40: 0, 41: 0, 42: 0, 43: 0, 44: 0, 45: 0, 46: 0, 47: 0, 48: 0, 49: 0, 50: 0, 51: 0, 52: 0, 53: 0, 54: 0, 55: 0, 56: 0, 57: 0, 58: 0, 59: 0, 60: 0, 61: 0, 62: 0, 63: 0, 64: 0, 65: 0, 66: 0, 67: 0, 68: 0, 69: 0, 70: 0, 71: 0, 72: 0, 73: 0, 74: 0, 75: 0, 76: 0, 77: 0, 78: 0, 79: 0, 80: 0, 81: 0, 82: 0, 83: 0, 84: 0, 85: 0, 86: 0, 87: 0, 88: 0, 89: 0, 90: 0, 91: 0, 92: 0, 93: 0, 94: 0, 95: 0} | None | None | 
| export_energy_from_pv_daily | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0} | None | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0} | 
| export_energy_from_pv_monthly | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | None | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | 
| export_energy_from_pv_yearly_starting_2019 | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | None | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | 
| battery_charge_energy_from_pv_today | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0, 31: 0.0, 32: 0.0, 33: 0.0, 34: 0.0, 35: 0.0, 36: 0.0, 37: 0.0, 38: 0.0, 39: 0.0, 40: 0.0, 41: 0.0, 42: 0.0, 43: 0.0, 44: 0.0, 45: 0.0, 46: 0.0, 47: 0.0, 48: 0.0, 49: 0.0, 50: 0.0, 51: 0.0, 52: 0.0, 53: 0.0, 54: 0.0, 55: 0.0, 56: 0.0, 57: 0.0, 58: 0.0, 59: 0.0, 60: 0.0, 61: 0.0, 62: 0.0, 63: 0.0, 64: 0.0, 65: 0.0, 66: 0.0, 67: 0.0, 68: 0.0, 69: 0.0, 70: 0.0, 71: 0.0, 72: 0.0, 73: 0.0, 74: 0.0, 75: 0.0, 76: 0.0, 77: 0.0, 78: 0.0, 79: 0.0, 80: 0.0, 81: 0.0, 82: 0.0, 83: 0.0, 84: 0.0, 85: 0.0, 86: 0.0, 87: 0.0, 88: 0.0, 89: 0.0, 90: 0.0, 91: 0.0, 92: 0.0, 93: 0.0, 94: 0.0, 95: 0.0} | None | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0, 31: 0.0, 32: 0.0, 33: 0.0, 34: 0.0, 35: 0.0, 36: 0.0, 37: 0.0, 38: 0.0, 39: 0.0, 40: 0.0, 41: 0.0, 42: 0.0, 43: 0.0, 44: 0.0, 45: 0.0, 46: 0.0, 47: 0.0, 48: 0.0, 49: 0.0, 50: 0.0, 51: 0.0, 52: 0.0, 53: 0.0, 54: 0.0, 55: 0.0, 56: 0.0, 57: 0.0, 58: 0.0, 59: 0.0, 60: 0.0, 61: 0.0, 62: 0.0, 63: 0.0, 64: 0.0, 65: 0.0, 66: 0.0, 67: 0.0, 68: 0.0, 69: 0.0, 70: 0.0, 71: 0.0, 72: 0.0, 73: 0.0, 74: 0.0, 75: 0.0, 76: 0.0, 77: 0.0, 78: 0.0, 79: 0.0, 80: 0.0, 81: 0.0, 82: 0.0, 83: 0.0, 84: 0.0, 85: 0.0, 86: 0.0, 87: 0.0, 88: 0.0, 89: 0.0, 90: 0.0, 91: 0.0, 92: 0.0, 93: 0.0, 94: 0.0, 95: 0.0} | 
| battery_charge_energy_from_pv | {0: 0.6, 1: 0.2, 2: 1.4, 3: 0.6, 4: 0.7, 5: 0.0, 6: 0.0, 7: 0.4, 8: 0.3, 9: 0.7, 10: 0.1, 11: 0.4, 12: 0.2, 13: 0.1, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0} | None | {0: 0.6, 1: 0.2, 2: 1.4, 3: 0.6, 4: 0.7, 5: 0.0, 6: 0.0, 7: 0.4, 8: 0.3, 9: 0.7, 10: 0.1, 11: 0.4, 12: 0.2, 13: 0.1, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0} | 
| battery_charge_energy_from_pv_monthly | {0: 5.7, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | None | {0: 5.7, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | 
| battery_charge_energy_from_pv_yearly_starting_2019 | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 12.1, 9: 5.7, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | None | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 12.1, 9: 5.7, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | 
| string_1_current | None | None | None | 
| string_2_current | None | None | None | 
| string_3_current | None | None | None | 
| string_4_current | None | None | None | 
| string_5_current | None | None | None | 
| string_6_current | None | None | None | 
| string_7_current | None | None | None | 
| string_8_current | None | None | None | 
| string_9_current | None | None | None | 
| string_10_current | None | None | None | 
| string_11_current | None | None | None | 
| string_12_current | None | None | None | 
| string_13_current | None | None | None | 
| string_14_current | None | None | None | 
| string_15_current | None | None | None | 
| string_16_current | None | None | None | 
| string_17_current | None | None | None | 
| string_18_current | None | None | None | 
| string_19_current | None | None | None | 
| string_20_current | None | None | None | 
| string_21_current | None | None | None | 
| string_22_current | None | None | None | 
| string_23_current | None | None | None | 
| string_24_current | None | None | None | 
| running_state | Running | Running | Running | 
| state_power_generated_from_pv | False | False | False | 
| state_battery_charging | False | False | False | 
| state_battery_discharging | False | False | False | 
| state_load_active | True | True | True | 
| state_feed_into_grid | False | False | False | 
| state_import_from_grid | True | True | True | 
| state_power_generated_from_load | False | False | False | 
| daily_pv_generation | 0.0 | 0.0 | 0.0 | 
| total_pv_generation | 37.5 | 37.5 | 37.5 | 
| daily_pv_export | 0.0 | 0.0 | 0.0 | 
| total_pv_export | 0.0 | 0.0 | 0.0 | 
| load_power_hybrid | 411 | 385 | 388 | 
| export_power_hybrid | -411 | -385 | -388 | 
| daily_battery_charge_from_pv | 0.0 | 0.0 | 0.0 | 
| total_battery_charge_from_pv | 17.8 | 17.8 | 17.8 | 
| co2_reduction | 26.2 | 0.0 | 26.2 | 
| daily_direct_energy_consumption_ | 0.0 | 0.0 | 0.0 | 
| total_direct_energy_consumption_ | 19.7 | 19.7 | 19.7 | 
| battery_voltage | 191.0 | 191.0 | 191.0 | 
| battery_current | 0.0 | 0.0 | 0.0 | 
| battery_power | 0 | 0 | 0 | 
| battery_level | 0.0 | 0.0 | 0.0 | 
| battery_state_of_health | 100.0 | 100.0 | 100.0 | 
| battery_temperature | 19.0 | 19.0 | 19.0 | 
| daily_battery_discharge_energy | 0.0 | 0.0 | 0.0 | 
| total_battery_discharge_energy | 107.1 | 107.1 | 107.1 | 
| self_consumption_of_day | 100.0 | 100.0 | 100.0 | 
| grid_state | None | 0 | None | 
| phase_a_current_ | 0.0 | 0.0 | 0.0 | 
| phase_b_current_ | 0.0 | 0.0 | 0.0 | 
| phase_c_current_ | 0.0 | 0.0 | 0.0 | 
| total_active_power_2 | 0 | 0 | 0 | 
| daily_imported_energy | 0.9 | 0.9 | 0.9 | 
| total_imported_energy | 281.8 | 281.8 | 281.8 | 
| battery_capacity | 9.6 | 96.0 | 9.6 | 
| daily_battery_charge_energy | 0.0 | 0.0 | 0.0 | 
| total_battery_charge_energy | 118.2 | 118.2 | 118.2 | 
| drm_state | 255 | 255 | 255 | 
| daily_exported_energy | 0.1 | 0.1 | 0.1 | 
| total_exported_energy | 26.2 | 26.2 | 26.2 | 
| inverter_alarm | 0.0 | 0.0 | 0.0 | 
| grid-side_fault | 0.0 | 0.0 | 0.0 | 
| system_fault1 | 0.0 | 0.0 | 0.0 | 
| system_fault2 | 0.0 | 0.0 | 0.0 | 
| dc-side_fault | 0.0 | 0.0 | 0.0 | 
| permanent_fault | 0.0 | 0.0 | 0.0 | 
| bdc-side_fault | 0.0 | 0.0 | 0.0 | 
| bdc-side_permanent_fault | 0.0 | 0.0 | 0.0 | 
| battery_fault | 0.0 | None | 0.0 | 
| battery_alarm | 0.0 | None | 0.0 | 
| bms_alarm | 0 | 0 | 0 | 
| bms_protection | 0 | 0 | 0 | 
| bms_fault1 | 0 | 0 | 0 | 
| bms_fault2 | 0 | 0 | 0 | 
| bms_alarm2 | 0 | 0 | 0 | 
| bms_status | None | 0 | None | 
| max_charging_current | None | 30 | None | 
| max_discharging_current | None | 27 | None | 
| warning | None | 0 | None | 
| protection | None | 0 | None | 
| fault1 | None | 0 | None | 
| fault2 | None | 0 | None | 
| soc | None | 0 | None | 
| soh | None | 0 | None | 
| battery_current_ | None | 0 | None | 
| battery_voltage_ | None | 0.0 | None | 
| cycle_count | None | 0.0 | None | 
| average_cell_voltage | None | 0 | None | 
| max_cell_voltage | None | 0 | None | 
| min_cell_voltage | None | 0 | None | 
| battery_pack_voltage | None | 0 | None | 
| average_cell_temp | -1 | 0 | -1 | 
| max_cell_temp | -1 | 0 | -1 | 
| min_cell_temp | -1 | 0 | -1 | 
| year | 2024 | 2024 | 2024 | 
| month | 1 | 1 | 1 | 
| day | 15 | 15 | 15 | 
| hour | 2 | 2 | 2 | 
| minute | 43 | 47 | 48 | 
| second | 20 | 53 | 44 | 
| start_stop | Start | Start | Start | 
| power_limitation_switch | Enable | Enable | Enable | 
| power_limitation_setting | 100.0 | 100.0 | 100.0 | 
| export_power_limitation | None | None | None | 
| export_power_limitation_value | None | None | None | 
| current_transformer_output_current | None | None | None | 
| current_transformer_range | None | None | None | 
| current_transformer | None | None | None | 
| export_power_limitation_percentage | None | None | None | 
| installed_pv_power | None | None | None | 
| power_factor_setting | None | None | None | 
| scheduling_achieve_active_overload | None | None | None | 
| night_svg_switch | None | None | None | 
| reactive_power_adjustment_mode | Off | Off | Off | 
| reactive_power_percentage_setting | -0.1 | -0.1 | -0.1 | 
| power_limitation_adjustment | None | None | None | 
| reactive_power_adjustment | -100.0 | -100.0 | -100.0 | 
| pid_recovery | None | None | None | 
| anti_pid | None | None | None | 
| fullday_pid_suppression | None | None | None | 
| start_stop_2 | Start | Start | Start | 
| ems_mode_selection | 0 | 0 | 0 | 
| battery_forced_charge_discharge_cmd | Stop | Stop | Stop | 
| battery_forced_charge_discharge_power | 0 | 0 | 0 | 
| battery_forced_charge_discharge_power_ | 0 | 0 | 0 | 
| Max_SoC | 100.0 | 100.0 | 100.0 | 
| Min_SoC | 5.0 | 5.0 | 5.0 | 
| export_power_limit | 12000 | 12000 | 12000 | 
| start_charging_power | 0.0 | 0.0 | 0.0 | 
| start_discharging_power | 0.0 | 0.0 | 0.0 | 
| energy_meter_comm | Enabled | Enabled | Enabled | 
| export_power_limitation_ | Enabled | Enabled | Enabled | 
| soc_reserve | 0 | 0 | 0 | 
| battery_max_charge_power | 10600.0 | 10600.0 | 10600.0 | 
| battery_max_discharge_power | 10600.0 | 10600.0 | 10600.0 | 
| battery_capacity_2 | 0.0 | 0.0 | 0.0 | 
| battery_charge_start_power | 0.0 | 0.0 | 0.0 | 
| battery_charge_stop_power | 0.0 | 0.0 | 0.0 | 
| master_slave_mode | Enabled | Enabled | Enabled | 
| master_slave_role | Master | Master | Master | 
| slave_count | 2 | 2 | 2 | 


# A2350415779
| Signal | pymodbus/192.168.13.80/2 | pymodbus/192.168.13.74/1 | 
| --- | --- | --- |
| protocol_number | 1094856704 | 1094791472 | 
| protocol_version | 16781568 | 16778496 | 
| arm_software_version | 16722 | 16722 | 
| dsp_software_version | 19780 | 19780 | 
| serial_number | A2350415779 | A2350415779 | 
| device_type_code | SH8.0RT-20 | SH8.0RT-20 | 
| nominal_output_power | 8.0 | 8.0 | 
| output_type | 3P4L | 3P4L | 
| daily_output_energy_pv_and_battery | 0.0 | 0.0 | 
| total_output_energy_pv_and_battery | 44.4 | 44.4 | 
| total_running_time | None | 0 | 
| internal_temperature | 28.4 | 28.3 | 
| total_apparent_power | 0 | 0 | 
| mppt_1_voltage | 0.0 | 0.0 | 
| mppt_1_current | 0.0 | 0.0 | 
| mppt_2_voltage | 0.0 | 0.0 | 
| mppt_2_current | 0.0 | 0.0 | 
| mppt_3_voltage | None | 0.0 | 
| mppt_3_current | None | 0.0 | 
| total_dc_power | 0 | 0 | 
| phase_a_voltage | 230.8 | 231.2 | 
| phase_b_voltage | 231.2 | 231.7 | 
| phase_c_voltage | 231.5 | 232.0 | 
| phase_a_current | 0.0 | 0.0 | 
| phase_b_current | 0.0 | 0.0 | 
| phase_c_current | 0.0 | 0.0 | 
| total_active_power | 0 | 0 | 
| total_reactive_power | 0 | 0 | 
| power_factor | 0.0 | 0.0 | 
| grid_frequency | 49.9 | 499.7 | 
| work_state_1 | None | 0 | 
| alarm_time_year | None | 0 | 
| alarm_time_month | None | 0 | 
| alarm_time_day | None | 0 | 
| alarm_time_hour | None | 0 | 
| alarm_time_minute | None | 0 | 
| alarm_time_second | None | 0 | 
| alarm_code_1 | None | 0 | 
| nominal_reactive_power | 4800.0 | 0.0 | 
| array_insulation_resistance | 955 | None | 
| active_power_regulation_setpoint | None | None | 
| reactive_power_regulation_setpoint | -1 | None | 
| work_state_2 | None | None | 
| meter_power | -1 | None | 
| meter_a_phase_power | -1 | None | 
| meter_b_phase_power | 65535 | None | 
| meter_c_phase_power | -65536 | None | 
| meter_load_power | -1 | None | 
| daily_export_energy | None | None | 
| total_export_energy | None | None | 
| daily_import_energy | None | None | 
| total_import_energy | None | None | 
| daily_direct_energy_consumption | None | None | 
| total_direct_energy_consumption | None | None | 
| daily_running_time | None | None | 
| mppt_4_voltage | None | None | 
| mppt_4_current | None | None | 
| mppt_5_voltage | None | None | 
| mppt_5_current | None | None | 
| mppt_6_voltage | None | None | 
| mppt_6_current | None | None | 
| mppt_7_voltage | None | None | 
| mppt_7_current | None | None | 
| mppt_8_voltage | None | None | 
| mppt_8_current | None | None | 
| monthly_power_yields | None | None | 
| mppt_9_voltage | None | None | 
| mppt_9_current | None | None | 
| mppt_10_voltage | None | None | 
| mppt_10_current | None | None | 
| mppt_11_voltage | None | None | 
| mppt_11_current | None | None | 
| mppt_12_voltage | None | None | 
| mppt_12_current | None | None | 
| total_power_yields | None | None | 
| negative_voltage_to_the_ground | -0.1 | None | 
| bus_voltage | 4.0 | None | 
| grid_frequency_ | 49.98 | None | 
| pid_work_state | None | None | 
| pid_alarm_code | None | None | 
| export_power | 0 | None | 
| meter_active_power | None | 0 | 
| meter_active_power_phase_a | None | 0 | 
| meter_active_power_phase_b | None | 0 | 
| meter_active_power_phase_c | None | 0 | 
| power_meter | 0 | None | 
| export_limit_min | 0.0 | 0.0 | 
| export_limit_max | 8000.0 | 8000.0 | 
| bdc_rated_power | 8000.0 | 8000.0 | 
| bms_max_charging_current | 0 | 0 | 
| bms_max_discharging_current | 0 | 0 | 
| battery_capacity_high_precision | 0.0 | 0.0 | 
| backup_power_phase_a | 0 | None | 
| backup_power_phase_b | 0 | None | 
| backup_power_phase_c | 0 | None | 
| backup_power_total | 0 | None | 
| pv_power_of_today | {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0, 17: 0, 18: 0, 19: 0, 20: 0, 21: 0, 22: 0, 23: 0, 24: 0, 25: 0, 26: 0, 27: 0, 28: 0, 29: 0, 30: 0, 31: 0, 32: 0, 33: 0, 34: 0, 35: 0, 36: 0, 37: 0, 38: 0, 39: 0, 40: 0, 41: 0, 42: 0, 43: 0, 44: 0, 45: 0, 46: 0, 47: 0, 48: 0, 49: 0, 50: 0, 51: 0, 52: 0, 53: 0, 54: 0, 55: 0, 56: 0, 57: 0, 58: 0, 59: 0, 60: 0, 61: 0, 62: 0, 63: 0, 64: 0, 65: 0, 66: 0, 67: 0, 68: 0, 69: 0, 70: 0, 71: 0, 72: 0, 73: 0, 74: 0, 75: 0, 76: 0, 77: 0, 78: 0, 79: 0, 80: 0, 81: 0, 82: 0, 83: 0, 84: 0, 85: 0, 86: 0, 87: 0, 88: 0, 89: 0, 90: 0, 91: 0, 92: 0, 93: 0, 94: 0, 95: 0} | None | 
| pv_energy_yields_daily | {0: 1.3, 1: 0.7, 2: 1.9, 3: 1.7, 4: 1.7, 5: 0.1, 6: 0.3, 7: 3.3, 8: 4.2, 9: 4.1, 10: 2.6, 11: 1.5, 12: 1.1, 13: 0.0, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0} | None | 
| pv_energy_yields_monthly | {0: 24.5, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | None | 
| pv_energy_yields_yearly_starting_2019 | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 19.9, 9: 24.5, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | None | 
| direct_power_consumption_from_pv_today | {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0, 17: 0, 18: 0, 19: 0, 20: 0, 21: 0, 22: 0, 23: 0, 24: 0, 25: 0, 26: 0, 27: 0, 28: 0, 29: 0, 30: 0, 31: 0, 32: 0, 33: 0, 34: 0, 35: 0, 36: 0, 37: 0, 38: 0, 39: 0, 40: 0, 41: 0, 42: 0, 43: 0, 44: 0, 45: 0, 46: 0, 47: 0, 48: 0, 49: 0, 50: 0, 51: 0, 52: 0, 53: 0, 54: 0, 55: 0, 56: 0, 57: 0, 58: 0, 59: 0, 60: 0, 61: 0, 62: 0, 63: 0, 64: 0, 65: 0, 66: 0, 67: 0, 68: 0, 69: 0, 70: 0, 71: 0, 72: 0, 73: 0, 74: 0, 75: 0, 76: 0, 77: 0, 78: 0, 79: 0, 80: 0, 81: 0, 82: 0, 83: 0, 84: 0, 85: 0, 86: 0, 87: 0, 88: 0, 89: 0, 90: 0, 91: 0, 92: 0, 93: 0, 94: 0, 95: 0} | None | 
| direct_power_consumption_from_pv_daily | {0: 1.3, 1: 0.7, 2: 1.9, 3: 1.7, 4: 1.7, 5: 0.1, 6: 0.3, 7: 3.3, 8: 4.2, 9: 4.1, 10: 2.6, 11: 1.5, 12: 1.1, 13: 0.0, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0} | None | 
| direct_energy_consumption_from_pv_monthly | {0: 24.5, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | None | 
| direct_energy_consumption_from_pv_yearly_starting_2019 | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 19.9, 9: 24.5, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | None | 
| export_power_from_pv_today | {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0, 17: 0, 18: 0, 19: 0, 20: 0, 21: 0, 22: 0, 23: 0, 24: 0, 25: 0, 26: 0, 27: 0, 28: 0, 29: 0, 30: 0, 31: 0, 32: 0, 33: 0, 34: 0, 35: 0, 36: 0, 37: 0, 38: 0, 39: 0, 40: 0, 41: 0, 42: 0, 43: 0, 44: 0, 45: 0, 46: 0, 47: 0, 48: 0, 49: 0, 50: 0, 51: 0, 52: 0, 53: 0, 54: 0, 55: 0, 56: 0, 57: 0, 58: 0, 59: 0, 60: 0, 61: 0, 62: 0, 63: 0, 64: 0, 65: 0, 66: 0, 67: 0, 68: 0, 69: 0, 70: 0, 71: 0, 72: 0, 73: 0, 74: 0, 75: 0, 76: 0, 77: 0, 78: 0, 79: 0, 80: 0, 81: 0, 82: 0, 83: 0, 84: 0, 85: 0, 86: 0, 87: 0, 88: 0, 89: 0, 90: 0, 91: 0, 92: 0, 93: 0, 94: 0, 95: 0} | None | 
| export_energy_from_pv_daily | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0} | None | 
| export_energy_from_pv_monthly | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | None | 
| export_energy_from_pv_yearly_starting_2019 | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | None | 
| battery_charge_energy_from_pv_today | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0, 31: 0.0, 32: 0.0, 33: 0.0, 34: 0.0, 35: 0.0, 36: 0.0, 37: 0.0, 38: 0.0, 39: 0.0, 40: 0.0, 41: 0.0, 42: 0.0, 43: 0.0, 44: 0.0, 45: 0.0, 46: 0.0, 47: 0.0, 48: 0.0, 49: 0.0, 50: 0.0, 51: 0.0, 52: 0.0, 53: 0.0, 54: 0.0, 55: 0.0, 56: 0.0, 57: 0.0, 58: 0.0, 59: 0.0, 60: 0.0, 61: 0.0, 62: 0.0, 63: 0.0, 64: 0.0, 65: 0.0, 66: 0.0, 67: 0.0, 68: 0.0, 69: 0.0, 70: 0.0, 71: 0.0, 72: 0.0, 73: 0.0, 74: 0.0, 75: 0.0, 76: 0.0, 77: 0.0, 78: 0.0, 79: 0.0, 80: 0.0, 81: 0.0, 82: 0.0, 83: 0.0, 84: 0.0, 85: 0.0, 86: 0.0, 87: 0.0, 88: 0.0, 89: 0.0, 90: 0.0, 91: 0.0, 92: 0.0, 93: 0.0, 94: 0.0, 95: 0.0} | None | 
| battery_charge_energy_from_pv | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: 0.0, 16: 0.0, 17: 0.0, 18: 0.0, 19: 0.0, 20: 0.0, 21: 0.0, 22: 0.0, 23: 0.0, 24: 0.0, 25: 0.0, 26: 0.0, 27: 0.0, 28: 0.0, 29: 0.0, 30: 0.0} | None | 
| battery_charge_energy_from_pv_monthly | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0} | None | 
| battery_charge_energy_from_pv_yearly_starting_2019 | {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: None, 16: None, 17: None, 18: None, 19: None} | None | 
| string_1_current | None | None | 
| string_2_current | None | None | 
| string_3_current | None | None | 
| string_4_current | None | None | 
| string_5_current | None | None | 
| string_6_current | None | None | 
| string_7_current | None | None | 
| string_8_current | None | None | 
| string_9_current | None | None | 
| string_10_current | None | None | 
| string_11_current | None | None | 
| string_12_current | None | None | 
| string_13_current | None | None | 
| string_14_current | None | None | 
| string_15_current | None | None | 
| string_16_current | None | None | 
| string_17_current | None | None | 
| string_18_current | None | None | 
| string_19_current | None | None | 
| string_20_current | None | None | 
| string_21_current | None | None | 
| string_22_current | None | None | 
| string_23_current | None | None | 
| string_24_current | None | None | 
| running_state | 8 | 5120 | 
| state_power_generated_from_pv | False | False | 
| state_battery_charging | False | False | 
| state_battery_discharging | False | False | 
| state_load_active | False | False | 
| state_feed_into_grid | False | False | 
| state_import_from_grid | False | False | 
| state_power_generated_from_load | False | False | 
| daily_pv_generation | 0.0 | 0.0 | 
| total_pv_generation | 44.4 | 44.4 | 
| daily_pv_export | 0.0 | 0.0 | 
| total_pv_export | 0.0 | 0.0 | 
| load_power_hybrid | 0 | 0 | 
| export_power_hybrid | 0 | 0 | 
| daily_battery_charge_from_pv | 0.0 | 0.0 | 
| total_battery_charge_from_pv | 0.0 | 0.0 | 
| co2_reduction | 31.0 | 0.0 | 
| daily_direct_energy_consumption_ | 0.0 | 0.0 | 
| total_direct_energy_consumption_ | 44.4 | 44.4 | 
| battery_voltage | 0.0 | 0.0 | 
| battery_current | 0.0 | 0.0 | 
| battery_power | 0 | 0 | 
| battery_level | 0.0 | 0.0 | 
| battery_state_of_health | 0.0 | 0.0 | 
| battery_temperature | 0.0 | 0.0 | 
| daily_battery_discharge_energy | 0.0 | 0.0 | 
| total_battery_discharge_energy | 0.0 | 0.0 | 
| self_consumption_of_day | 100.0 | 100.0 | 
| grid_state | None | 0 | 
| phase_a_current_ | 0.0 | 0.0 | 
| phase_b_current_ | 0.0 | 0.0 | 
| phase_c_current_ | 0.0 | 0.0 | 
| total_active_power_2 | 0 | 0 | 
| daily_imported_energy | 0.0 | 0.0 | 
| total_imported_energy | 0.0 | 0.0 | 
| battery_capacity | 0.0 | 0.0 | 
| daily_battery_charge_energy | 0.0 | 0.0 | 
| total_battery_charge_energy | 0.0 | 0.0 | 
| drm_state | 255 | 255 | 
| daily_exported_energy | 0.0 | 0.0 | 
| total_exported_energy | 0.0 | 0.0 | 
| inverter_alarm | 0.0 | 0.0 | 
| grid-side_fault | 0.0 | 0.0 | 
| system_fault1 | 0.0 | 0.0 | 
| system_fault2 | 0.0 | 0.0 | 
| dc-side_fault | 0.0 | 0.0 | 
| permanent_fault | 0.0 | 0.0 | 
| bdc-side_fault | 0.0 | 0.0 | 
| bdc-side_permanent_fault | 0.0 | 0.0 | 
| battery_fault | 0.0 | None | 
| battery_alarm | 0.0 | None | 
| bms_alarm | 0 | 0 | 
| bms_protection | 0 | 0 | 
| bms_fault1 | 0 | 0 | 
| bms_fault2 | 0 | 0 | 
| bms_alarm2 | 0 | 0 | 
| bms_status | None | 0 | 
| max_charging_current | None | 0 | 
| max_discharging_current | None | 0 | 
| warning | None | 0 | 
| protection | None | 0 | 
| fault1 | None | 0 | 
| fault2 | None | 0 | 
| soc | None | 0 | 
| soh | None | 0 | 
| battery_current_ | None | 0 | 
| battery_voltage_ | None | 0.0 | 
| cycle_count | None | 0.0 | 
| average_cell_voltage | None | 0 | 
| max_cell_voltage | None | 0 | 
| min_cell_voltage | None | 0 | 
| battery_pack_voltage | None | 0 | 
| average_cell_temp | -1 | 0 | 
| max_cell_temp | -1 | 0 | 
| min_cell_temp | -1 | 0 | 
| year | 2024 | 2024 | 
| month | 1 | 1 | 
| day | 15 | 15 | 
| hour | 2 | 2 | 
| minute | 49 | 54 | 
| second | 52 | 32 | 
| start_stop | Start | Start | 
| power_limitation_switch | Enable | Enable | 
| power_limitation_setting | 0.0 | 0.0 | 
| export_power_limitation | None | None | 
| export_power_limitation_value | None | None | 
| current_transformer_output_current | None | None | 
| current_transformer_range | None | None | 
| current_transformer | None | None | 
| export_power_limitation_percentage | None | None | 
| installed_pv_power | None | None | 
| power_factor_setting | None | None | 
| scheduling_achieve_active_overload | None | None | 
| night_svg_switch | None | None | 
| reactive_power_adjustment_mode | Off | Off | 
| reactive_power_percentage_setting | -0.1 | -0.1 | 
| power_limitation_adjustment | None | None | 
| reactive_power_adjustment | -100.0 | -100.0 | 
| pid_recovery | None | None | 
| anti_pid | None | None | 
| fullday_pid_suppression | None | None | 
| start_stop_2 | Start | Start | 
| ems_mode_selection | 0 | 0 | 
| battery_forced_charge_discharge_cmd | Stop | Stop | 
| battery_forced_charge_discharge_power | 0 | 0 | 
| battery_forced_charge_discharge_power_ | 0 | 0 | 
| Max_SoC | 100.0 | 100.0 | 
| Min_SoC | 0.0 | 0.0 | 
| export_power_limit | 8000 | 8000 | 
| start_charging_power | 0.0 | 0.0 | 
| start_discharging_power | 0.0 | 0.0 | 
| energy_meter_comm | Enabled | Enabled | 
| export_power_limitation_ | Enabled | Enabled | 
| soc_reserve | 0 | 0 | 
| battery_max_charge_power | 10600.0 | 10600.0 | 
| battery_max_discharge_power | 10600.0 | 10600.0 | 
| battery_capacity_2 | 0.0 | 0.0 | 
| battery_charge_start_power | 0.0 | 0.0 | 
| battery_charge_stop_power | 0.0 | 0.0 | 
| master_slave_mode | Enabled | Enabled | 
| master_slave_role | Slave 1 | Slave 1 | 
| slave_count | 2 | 2 | 


