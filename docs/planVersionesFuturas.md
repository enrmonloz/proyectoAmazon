Sí: eso apunta casi seguro a **keyring/wallet inestable o cambiado entre sesiones**.

Cuando cambias entre Plasma/KDE, Niri Wayland, GNOME components, etc., Brave puede elegir otro backend de secretos. Brave/Chromium en Linux puede usar distintos almacenes (`gnome-libsecret`, `kwallet`, `kwallet5`, `kwallet6`, `basic`), y Brave tiene flags explícitos para fijarlo con `--password-store=...`. ([GitHub][1]) Si el navegador no encuentra la misma clave de cifrado que usó antes, las cookies/sesiones parecen “perdidas”, aunque muchas veces no se han borrado: no se pueden descifrar con el backend actual. Esto encaja con problemas descritos al cambiar entre escritorios que usan libsecret/GNOME Keyring y KWallet. ([Brave Community][2])

## 1. Primero: no abras Brave de dos maneras distintas

Cierra Brave completamente:

```bash
pkill -f brave
```

Comprueba que no queda nada:

```bash
pgrep -a brave || echo "OK: Brave cerrado"
```

---

# 2. Averigua qué backend recupera tus sesiones

Prueba **uno**. Mira si tus cuentas vuelven.

## Prueba con KWallet 6

```bash
brave-browser --password-store=kwallet6
```

Si no existe ese comando:

```bash
brave-browser-stable --password-store=kwallet6
```

Mira si siguen tus sesiones/cookies.

Cierra Brave:

```bash
pkill -f brave
```

## Prueba con GNOME libsecret

```bash
brave-browser --password-store=gnome-libsecret
```

o:

```bash
brave-browser-stable --password-store=gnome-libsecret
```

El que haga que “vuelvan” tus inicios de sesión es el backend correcto que debes fijar.

---

# 3. Mi recomendación para Niri/DMS: usar `gnome-libsecret`

En Niri es más estable usar **GNOME Keyring/libsecret** como backend común para Brave, apps Electron y secretos varios.

Instala/asegura:

```bash
sudo apt install --reinstall gnome-keyring libsecret-1-0 seahorse
```

Comprueba que el daemon existe:

```bash
pgrep -a gnome-keyring || echo "gnome-keyring no está corriendo"
```

Arráncalo para probar:

```bash
eval "$(gnome-keyring-daemon --start --components=secrets,ssh,pkcs11)"
export SSH_AUTH_SOCK
```

Ahora prueba Brave:

```bash
brave-browser --password-store=gnome-libsecret
```

---

# 4. Hacerlo permanente para Brave

Copia el launcher a tu usuario:

```bash
mkdir -p ~/.local/share/applications
cp /usr/share/applications/brave-browser.desktop ~/.local/share/applications/brave-browser.desktop
```

Edita:

```bash
nano ~/.local/share/applications/brave-browser.desktop
```

Busca todas las líneas que empiecen por:

```ini
Exec=
```

Y cambia, por ejemplo, esto:

```ini
Exec=/usr/bin/brave-browser-stable %U
```

a esto:

```ini
Exec=/usr/bin/brave-browser-stable --password-store=gnome-libsecret %U
```

Si quieres Brave Wayland nativo:

```ini
Exec=/usr/bin/brave-browser-stable --password-store=gnome-libsecret --ozone-platform=wayland %U
```

Haz lo mismo en las otras líneas `Exec=...` que aparezcan.

Luego:

```bash
update-desktop-database ~/.local/share/applications
```

Cierra sesión y vuelve a entrar.

Comprueba que el launcher usado es el local:

```bash
grep '^Exec=' ~/.local/share/applications/brave-browser.desktop
```

---

# 5. Asegura que GNOME Keyring se abre al iniciar sesión

Comprueba PAM:

```bash
grep -R "pam_gnome_keyring" /etc/pam.d/sddm*
```

Si no sale nada, ejecuta:

```bash
sudo pam-auth-update
```

Activa:

```text
GNOME Keyring Daemon - Login keyring management
```

Después reinicia sesión completa.

En Niri, además, puedes dejar esto en `~/.config/niri/config.kdl`:

```kdl
spawn-at-startup "gnome-keyring-daemon" "--start" "--components=secrets,ssh,pkcs11"
```

Pero ojo: si esa línea ya la tienes, asegúrate de que no haya texto roto delante. Antes tu config tenía una línea sin `//` al principio.

Valida:

```bash
niri validate
```

---

# 6. WiFi: evita depender de wallet/keyring

Para WiFi, lo más robusto en un sistema Niri es guardar la contraseña en NetworkManager como conexión de sistema.

Lista conexiones WiFi:

```bash
nmcli -t -f NAME,TYPE connection show | grep wireless
```

Para tu red, cambia `"NOMBRE_WIFI"`:

```bash
nmcli connection modify "NOMBRE_WIFI" 802-11-wireless-security.psk-flags 0
nmcli connection modify "NOMBRE_WIFI" connection.permissions ""
```

`psk-flags` controla cómo NetworkManager maneja la clave WiFi; en NetworkManager los flags de secretos incluyen `none (0x0)`, `agent-owned (0x1)`, `not-saved (0x2)` y `not-required (0x4)`. ([NetworkManager][3]) Para WPA/WPA2/WPA3 personal, la clave vive en la propiedad `psk` de `802-11-wireless-security`, y `psk-flags` decide cómo se gestiona. ([NetworkManager][4])

Si no hay contraseña guardada, ponla tú localmente:

```bash
nmcli connection modify "NOMBRE_WIFI" 802-11-wireless-security.psk "TU_CONTRASEÑA_WIFI"
nmcli connection modify "NOMBRE_WIFI" 802-11-wireless-security.psk-flags 0
nmcli connection up "NOMBRE_WIFI"
```

Esto la guarda en:

```text
/etc/NetworkManager/system-connections/
```

con permisos de root, y deja de depender de KWallet/GNOME Keyring para reconectar.

---

# 7. Apps que pierden sesión

Apps tipo Electron/Chromium también pueden depender de Secret Service/libsecret. Por eso arreglar `gnome-keyring` suele estabilizar:

```bash
sudo apt install --reinstall gnome-keyring libsecret-1-0
```

Y en Niri:

```kdl
spawn-at-startup "gnome-keyring-daemon" "--start" "--components=secrets,ssh,pkcs11"
```

---

## Plan recomendado

Haz esto:

```bash
sudo apt install --reinstall gnome-keyring libsecret-1-0 seahorse
```

Luego prueba:

```bash
pkill -f brave
brave-browser --password-store=gnome-libsecret
```

Si tus sesiones vuelven, fija `--password-store=gnome-libsecret` en:

```text
~/.local/share/applications/brave-browser.desktop
```

Y para WiFi:

```bash
nmcli -t -f NAME,TYPE connection show | grep wireless
nmcli connection modify "NOMBRE_WIFI" 802-11-wireless-security.psk-flags 0
nmcli connection modify "NOMBRE_WIFI" connection.permissions ""
```

La clave es: **elige un único backend de secretos y no dejes que Brave lo autodetecte según la sesión**.

[1]: https://github.com/brave/brave-browser/issues/32314?utm_source=chatgpt.com "Improve password storage backend detection logic on Linux"
[2]: https://community.brave.app/t/brave-keeps-losing-logins-across-desktop-environments-hyprland-kde-gnome/635736?utm_source=chatgpt.com "Brave Keeps Losing Logins Across Desktop Environments ..."
[3]: https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html?utm_source=chatgpt.com "nm-settings-nmcli: NetworkManager Reference Manual"
[4]: https://networkmanager.dev/docs/api/1.52.0/settings-802-11-wireless-security.html?utm_source=chatgpt.com "802-11-wireless-security: NetworkManager Reference Manual"
