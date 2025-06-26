# Changelog

## [Unreleased]

### Fixed
- **Device Discovery for Specific IPs**: Fixed issue where MQTT service could not find devices when using specific IP addresses (e.g., NETWORK=192.168.0.90) instead of broadcast addresses. The `broadcast_scan` method now correctly handles both broadcast communication (for .255 addresses) and direct UDP communication (for specific IP addresses). This resolves issue #44 where users reported devices not being discovered when specifying individual device IPs.

### Technical Details
- Modified `DeviceCommunicator.broadcast_scan()` in `device_communication.py` to detect IP type
- For broadcast IPs (ending in .255): Uses SO_BROADCAST socket option with local address binding
- For specific IPs: Uses direct UDP communication without broadcast flag with remote address connection
- Both subnet scanning and individual device discovery now work correctly with the appropriate communication method

### Migration Notes
- No breaking changes - existing configurations continue to work
- Users can now reliably use specific device IPs in NETWORK environment variable
- Broadcast discovery functionality remains unchanged