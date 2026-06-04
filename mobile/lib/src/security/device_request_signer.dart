import 'dart:typed_data';

class SignedRequestHeaders {
  const SignedRequestHeaders(this.values);

  final Map<String, String> values;
}

abstract class DeviceRequestSigner {
  Future<SignedRequestHeaders> sign({
    required String method,
    required String pathWithQuery,
    required Uint8List body,
  });
}

class UnavailableDeviceRequestSigner implements DeviceRequestSigner {
  const UnavailableDeviceRequestSigner();

  @override
  Future<SignedRequestHeaders> sign({
    required String method,
    required String pathWithQuery,
    required Uint8List body,
  }) {
    throw StateError('Device request signer is not configured.');
  }
}
