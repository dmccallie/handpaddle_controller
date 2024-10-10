# test chooser

import win32com.client

def open_ascom_chooser(device_type="Telescope"):
    chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
    chooser.DeviceType = device_type
    prog_id = chooser.Choose("")

    if prog_id:
        device = win32com.client.Dispatch(prog_id)
        return device
    else:
        return None

# Example usage:
telescope = open_ascom_chooser("Telescope")
if telescope:
    print(f"Selected telescope: {telescope.Name}")
else:
    print("No telescope selected")


