package app.act.agentic_control_tower

import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

// FlutterFragmentActivity (not FlutterActivity) is required so the native
// BiometricPrompt can attach to a FragmentActivity.
class MainActivity : FlutterFragmentActivity() {
    private lateinit var keystoreSigner: KeystoreSigner

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        keystoreSigner = KeystoreSigner { this }
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, KeystoreSigner.CHANNEL)
            .setMethodCallHandler { call, result -> keystoreSigner.handle(call, result) }
    }
}
