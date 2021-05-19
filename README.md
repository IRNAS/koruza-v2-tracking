# koruza-v2-tracking

## Description
The goal of KORUZA v2 Pro Tracking is to implement and provide a easy to use Alignment interface written in Python. Using this interface integrators and KORUZA v2 Pro users can write, test and deploy their own Auto Alignment and Tracking algorithms.

The Alignment interface provides full control over both units with the following actions:
* move selected unit to desired position
* move selected unit to it's maximum
* get current position of selected unit
* set strategy for maxima selection
* reset maximum of selected unit
* start reading data from both units

For Automatic Alignment and Tracking to work units have to be configured according to the `config.json` file described in the [device management](https://github.com/IRNAS/koruza-v2-device-management) repository.

## Algorithms
The goal of alignment algorithms is to align both KORUZA v2 Pro units in a position where the strength of the received optical signal is maximized on both units. This can be done in various ways, applying different algorithms.

We have currently implemented a Spiral Scan Align Algorithm. More Auto Alignment Algorithms and Tracking techniques are planned to be released in the future.

## Guide to Implementation
_Coming soon..._

This section will include all relevant instructions on how a user must implement their own algorithm such that it is compatible with the alignment engine and other KORUZA sotware packages.

## License
Firmware and software originating from KORUZA v2 Pro project, including KORUZA v2 Pro Tracking, is licensed under [GNU General Public License v3.0](https://github.com/IRNAS/koruza-v2-tracking/blob/master/LICENSE).

Open-source licensing means the hardware, firmware, software and documentation may be used without paying a royalty, and knowing one will be able to use their version forever. One is also free to make changes, but if one shares these changes, they have to do so under the same conditions they are using themselves. KORUZA, KORUZA v2 Pro and IRNAS are all names and marks of IRNAS LTD. These names and terms may only be used to attribute the appropriate entity as required by the Open Licence referred to above. The names and marks may not be used in any other way, and in particular may not be used to imply endorsement or authorization of any hardware one is designing, making or selling.
