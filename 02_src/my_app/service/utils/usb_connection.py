def _normalized(value):
    return str(
        value or ""
    ).strip().upper()


def probe_usb_readers(config: dict):
    import pythoncom
    import wmi
    from smartcard.System import readers

    com_initialized = False
    pcsc_reader_names = []
    pnp_device_ids = []
    pcsc_error = None
    pnp_error = None

    try:
        pythoncom.CoInitialize()
        com_initialized = True

        try:
            pcsc_reader_names = [
                str(reader)
                for reader in readers()
            ]
        except Exception as ex:
            pcsc_error = str(ex)

        try:
            wmi_client = wmi.WMI()

            pnp_device_ids = [
                _normalized(
                    getattr(
                        device,
                        "DeviceID",
                        "",
                    )
                )
                for device
                in wmi_client.Win32_PnPEntity()
            ]
        except Exception as ex:
            pnp_error = str(ex)

        devices = config.get(
            "devices",
            {},
        )

        if not isinstance(
            devices,
            dict,
        ):
            devices = {}

        results = {}

        for location in (
            "入口",
            "出口",
        ):
            device = devices.get(
                location,
                {},
            )

            if not isinstance(
                device,
                dict,
            ):
                device = {}

            name = str(
                device.get("name")
                or ""
            ).strip()

            vid = _normalized(
                device.get("vid")
            )
            pid = _normalized(
                device.get("pid")
            )
            serial = _normalized(
                device.get("serial")
            )

            configured = bool(
                name
                and vid
                and pid
                and serial
            )

            usb_token = (
                f"VID_{vid}&PID_{pid}"
            )

            pnp_connected = (
                configured
                and any(
                    usb_token in device_id
                    and serial in device_id
                    for device_id
                    in pnp_device_ids
                )
            )

            pcsc_connected = (
                configured
                and any(
                    name.casefold()
                    in reader_name.casefold()
                    or reader_name.casefold()
                    in name.casefold()
                    for reader_name
                    in pcsc_reader_names
                )
            )

            # WMIが使えない場合でもPC/SCで認識できれば接続中
            connected = (
                pcsc_connected
                and pnp_connected
            )

            probe_available = (
                pcsc_error is None
                and pnp_error is None
            )

            error_messages = [
                message
                for message in (
                    pcsc_error,
                    pnp_error,
                )
                if message
            ]

            results[location] = {
                "configured": configured,
                "pnp_connected": pnp_connected,
                "pcsc_connected": pcsc_connected,
                "connected": connected,
                "probe_available": probe_available,
                "error": " / ".join(
                    error_messages
                ),
                "pcsc_readers": (
                    pcsc_reader_names.copy()
                ),
            }

        return results

    finally:
        if com_initialized:
            pythoncom.CoUninitialize()