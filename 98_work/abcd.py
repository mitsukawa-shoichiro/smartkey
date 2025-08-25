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
if __name__ == "__main__":
    asyncio.run(main())
