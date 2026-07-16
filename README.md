SAMP Launcher Mobile
Launcher de servidores SA-MP (San Andreas Multiplayer) para Android, feito com
Kivy. Lista de favoritos, ping/players em tempo real,
nickname salvo e conexão rápida por IP:porta.
O que mudou em relação à versão desktop (Tkinter)
Interface reconstruída em Kivy (touch-friendly, telas grandes por padrão,
botões maiores, sem menus de mouse).
RecycleView no lugar do Treeview para listar servidores (mais leve em
telas de celular com muitos itens).
Configuração salva em user_data_dir do app (pasta correta e sandboxed no
Android), em vez da pasta do script.
"Jogar" não abre mais um .exe — o SA-MP não tem cliente oficial para
Android/iOS. O app agora:
Tenta abrir a URI samp://ip:porta?nick=Nome, que é reconhecida por
alguns clientes SA-MP não oficiais para Android que registram esse
scheme.
Sempre copia ip:porta para a área de transferência como fallback, para
colar manualmente no cliente que você usa.
Consulta ao servidor (protocolo UDP SAMP...i) roda em thread separada com
Clock/@mainthread do Kivy, para não travar a UI.
Rodando no desktop para testar
Bash
Gerando o APK (Android)
Buildozer só funciona em Linux/WSL (não builda diretamente no Windows).
Bash
O primeiro build baixa o Android SDK/NDK automaticamente (pode demorar).
O APK final fica em bin/sampLauncher-1.0-arm64-v8a-debug.apk.
Instale no aparelho com:
Bash
Limitações conhecidas
Sem cliente oficial de SA-MP para mobile, o "Jogar" depende de um app de
terceiros que registre samp:// no seu Android, ou de colar o endereço
manualmente.
Seleção de servidor para remoção está simplificada (remove o último item);
para produção, vale adicionar seleção por toque em cada linha
(on_touch_down no ServerRow).
iOS exige build via kivy-ios/Xcode em macOS — não coberto aqui.
