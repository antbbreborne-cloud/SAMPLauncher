[app]
title = SAMP Launcher
package.name = sampLauncher
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

# Permissão de rede (necessária para consultar os servidores via UDP)
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# Registra o scheme samp:// para que o app possa ser aberto por outros
# apps/links usando samp://ip:porta (opcional, útil para deep-linking)
# android.manifest.intent_filters = intent_filters.xml

android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
