# /boot/firmware/config.txt dosyasını düzenle (veya /boot/config.txt)
sudo nano /boot/firmware/config.txt

# USB OTG Modu etkinleştirme
dtoverlay=dwc2,dr_mode=peripheral
otg_mode=1

# /etc/modules dosyasını düzenle
sudo nano /etc/modules

dwc2
libcomposite

# Betik oluştur
sudo nano /usr/local/bin/setup_usb_gadget.sh

#!/bin/bash

# USB Gadget modunu temizle (eğer varsa)
if [ -d /sys/kernel/config/usb_gadget/switchpro ]; then
    echo "" > /sys/kernel/config/usb_gadget/switchpro/UDC
    rm -rf /sys/kernel/config/usb_gadget/switchpro
fi

# USB Gadget dizini oluştur
mkdir -p /sys/kernel/config/usb_gadget/switchpro
cd /sys/kernel/config/usb_gadget/switchpro

# Nintendo Switch Pro controller kimliklerini ayarla
echo 0x057E > idVendor  # Nintendo
echo 0x2009 > idProduct # Pro Controller

# İngilizce ABD ayarla
mkdir -p strings/0x409
echo "Nintendo" > strings/0x409/manufacturer
echo "Pro Controller" > strings/0x409/product
echo "000000000001" > strings/0x409/serialnumber

# Yapılandırma oluştur
mkdir -p configs/c.1/strings/0x409
echo "Pro Controller Config" > configs/c.1/strings/0x409/configuration
echo 500 > configs/c.1/MaxPower

# HID fonksiyonu ekle
mkdir -p functions/hid.usb0
echo 0 > functions/hid.usb0/protocol
echo 0 > functions/hid.usb0/subclass
echo 64 > functions/hid.usb0/report_length

# Pro Controller HID tanımlayıcısı (basitleştirilmiş)
echo -ne \\x05\\x01\\x09\\x05\\xa1\\x01\\x15\\x00\\x25\\x01\\x35\\x00\\x45\\x01\\x75\\x01\\x95\\x10\\x05\\x09\\x19\\x01\\x29\\x10\\x81\\x02\\x05\\x01\\x25\\x07\\x46\\x3b\\x01\\x75\\x04\\x95\\x01\\x65\\x14\\x09\\x39\\x81\\x42\\x65\\x00\\x95\\x01\\x81\\x01\\x26\\xff\\x00\\x46\\xff\\x00\\x09\\x30\\x09\\x31\\x09\\x32\\x09\\x35\\x75\\x08\\x95\\x04\\x81\\x02\\x06\\x00\\xff\\x09\\x20\\x95\\x01\\x81\\x02\\x0a\\x21\\x26\\x95\\x08\\x81\\x02\\x0a\\x22\\x26\\x95\\x08\\x81\\x02\\x95\\x06\\x81\\x01\\xc0 > functions/hid.usb0/report_desc

# Sembolik bağlantı oluştur
ln -s functions/hid.usb0 configs/c.1/

# UDC'yi etkinleştir - RP1 (Raspberry Pi 5's USB controller)
ls /sys/class/udc > UDC

# İzinleri ayarla
chmod 777 /dev/hidg0

sudo chmod +x /usr/local/bin/setup_usb_gadget.sh
sudo /usr/local/bin/setup_usb_gadget.sh
