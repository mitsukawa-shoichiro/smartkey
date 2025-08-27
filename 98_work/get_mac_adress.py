import asyncio
from bleak import BleakScanner


async def main():
    devices = await BleakScanner.discover(return_adv=True)
    for d, adv in devices.values():

        if 1370 in adv.manufacturer_data:

            print("Address:", d.address)
            print("Name:", d.name or adv.local_name)
            print("RSSI:", adv.rssi)
            print("Service UUIDs:", adv.service_uuids)
            print("Manufacturer Data:", adv.manufacturer_data)
            return d.address


def mac_address_type(mac):

    first = int(mac.split(":")[0], 16)
    top2 = (first & 0xC0) >> 6
    if top2 == 3:
        return "Random Static (ほぼ固定 — 短期では変わらない)"
    elif top2 == 1:
        return "Resolvable Private Address (RPA) — 回転する可能性あり"
    elif top2 == 0:
        return "Non-resolvable Private Address — 回転・匿名化向け"
    else:
        return "Reserved/Unknown"


if __name__ == "__main__":
    asyncio.run(main())
    # print(mac_address_type("DF:FD:0D:D3:43:8D"))
