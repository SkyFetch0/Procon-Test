#!/usr/bin/env python3
import time
import math
import struct
import threading
import os
import platform

# Xbox 360 kontrolcüsünü okumak için
try:
    import pygame
except ImportError:
    print("pygame kütüphanesi gerekli. Yüklemek için: pip install pygame")
    exit(1)

# USB HID iletişimi için - Raspberry Pi'de çalışacak
# Windows'ta sadece kontrolcüyü okumak için kullanılacak
try:
    import usb.core
    import usb.util
    HAS_USB = True
except ImportError:
    print("pyusb kütüphanesi bulunamadı. Windows'ta kontrolcü emülasyonu sınırlı olacak.")
    print("Yüklemek için: pip install pyusb")
    HAS_USB = False

class SwitchProEmulator:
    # Nintendo Switch Pro Controller USB tanımlayıcıları
    SWITCH_VENDOR_ID = 0x057E
    SWITCH_PRODUCT_ID = 0x2009
    PACKET_SIZE = 64
    
    # Xbox 360 kontrolcü tanımlayıcıları
    XBOX_BUTTON_A = 0
    XBOX_BUTTON_B = 1
    XBOX_BUTTON_X = 2
    XBOX_BUTTON_Y = 3
    XBOX_BUTTON_LB = 4
    XBOX_BUTTON_RB = 5
    XBOX_BUTTON_BACK = 6
    XBOX_BUTTON_START = 7
    XBOX_BUTTON_HOME = 8
    XBOX_BUTTON_LS = 9
    XBOX_BUTTON_RS = 10
    
    # Diğer sabitler
    RUMBLE_NEUTRAL = (0x00, 0x01, 0x40, 0x40)
    
    def __init__(self):
        self.running = False
        self.system = platform.system()
        
        # Xbox kontrolcüsünü başlat
        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() == 0:
            print("Bağlı kontrolcü bulunamadı!")
            exit(1)
        
        self.controller = pygame.joystick.Joystick(0)
        self.controller.init()
        print(f"Bağlı kontrolcü: {self.controller.get_name()}")
        
        # Raspberry Pi'de USB gadget modunu yapılandır
        if self.system == "Linux" and HAS_USB and os.path.exists("/sys/kernel/config/usb_gadget"):
            self.setup_usb_gadget()
            self.gadget_mode = True
            print("USB Gadget modu etkinleştirildi")
        else:
            self.gadget_mode = False
            print("USB Gadget modu kullanılamıyor - Emülasyon doğrudan çalışmayacak")
            if self.system == "Windows":
                print("Windows sistemlerde doğrudan USB cihaz emülasyonu desteklenmiyor.")
                print("Önerilen: Arduino/Teensy gibi bir mikrodenetleyici kullanarak USB HID cihazını emüle edin.")
    
    def setup_usb_gadget(self):
        # Not: Bu kısım sadece Raspberry Pi'de ve root olarak çalıştırıldığında çalışır
        try:
            # USB gadget modunu yapılandır
            os.system("modprobe libcomposite")
            
            # USB gadget dizini oluştur
            gadget_dir = "/sys/kernel/config/usb_gadget/switchpro"
            os.makedirs(gadget_dir, exist_ok=True)
            
            # Üretici ve ürün ID'leri ayarla
            with open(f"{gadget_dir}/idVendor", "w") as f:
                f.write(f"{self.SWITCH_VENDOR_ID:04x}")
            with open(f"{gadget_dir}/idProduct", "w") as f:
                f.write(f"{self.SWITCH_PRODUCT_ID:04x}")
            
            # İngilizce ABD ayarla
            os.makedirs(f"{gadget_dir}/strings/0x409", exist_ok=True)
            with open(f"{gadget_dir}/strings/0x409/manufacturer", "w") as f:
                f.write("Nintendo")
            with open(f"{gadget_dir}/strings/0x409/product", "w") as f:
                f.write("Pro Controller")
            
            # Yapılandırma oluştur
            os.makedirs(f"{gadget_dir}/configs/c.1/strings/0x409", exist_ok=True)
            with open(f"{gadget_dir}/configs/c.1/strings/0x409/configuration", "w") as f:
                f.write("Pro Controller Config")
            
            # HID fonksiyonu ekle
            os.makedirs(f"{gadget_dir}/functions/hid.usb0", exist_ok=True)
            with open(f"{gadget_dir}/functions/hid.usb0/protocol", "w") as f:
                f.write("0")
            with open(f"{gadget_dir}/functions/hid.usb0/subclass", "w") as f:
                f.write("0")
            with open(f"{gadget_dir}/functions/hid.usb0/report_length", "w") as f:
                f.write(f"{self.PACKET_SIZE}")
            
            # HID tanımlayıcısını yaz
            # Not: Gerçek bir Pro Controller'ın HID tanımlayıcısını kullanmak gerekir
            # Bu sadece temel bir örnektir
            report_desc = [
                0x05, 0x01,  # USAGE_PAGE (Generic Desktop)
                0x09, 0x05,  # USAGE (Game Pad)
                0xa1, 0x01,  # COLLECTION (Application)
                # HID descriptor burada devam eder...
                0xc0         # END_COLLECTION
            ]
            
            with open(f"{gadget_dir}/functions/hid.usb0/report_desc", "wb") as f:
                f.write(bytes(report_desc))
            
            # Sembolik bağlantı oluştur
            os.symlink(f"{gadget_dir}/functions/hid.usb0", f"{gadget_dir}/configs/c.1/hid.usb0")
            
            # UDC'yi etkinleştir
            # Not: Raspberry Pi'nin USB denetleyicisinin adını bulmak gerekir
            # Bu genellikle "dwc2" veya benzeri bir isimdir
            udc_name = os.listdir("/sys/class/udc")[0]
            with open(f"{gadget_dir}/UDC", "w") as f:
                f.write(udc_name)
            
            print("USB gadget oluşturuldu")
        except Exception as e:
            print(f"USB gadget modunu yapılandırırken hata: {e}")
            print("Not: Bu işlem için root yetkileri gereklidir")
    
    def xbox_to_switch_buttons(self):
        # Xbox düğmeleri durumunu oku
        pygame.event.pump()  # Joystick durumunu güncelle
        
        # Düğme durumlarını al
        buttons = {
            'A': self.controller.get_button(self.XBOX_BUTTON_A),
            'B': self.controller.get_button(self.XBOX_BUTTON_B),
            'X': self.controller.get_button(self.XBOX_BUTTON_X),
            'Y': self.controller.get_button(self.XBOX_BUTTON_Y),
            'L': self.controller.get_button(self.XBOX_BUTTON_LB),
            'R': self.controller.get_button(self.XBOX_BUTTON_RB),
            'ZL': self.controller.get_axis(4) > 0.5,  # Sol tetik
            'ZR': self.controller.get_axis(5) > 0.5,  # Sağ tetik
            'MINUS': self.controller.get_button(self.XBOX_BUTTON_BACK),
            'PLUS': self.controller.get_button(self.XBOX_BUTTON_START),
            'HOME': self.controller.get_button(self.XBOX_BUTTON_HOME),
            'CAPTURE': False,  # Xbox 360'ta eşleşen düğme yok
            'LS': self.controller.get_button(self.XBOX_BUTTON_LS),
            'RS': self.controller.get_button(self.XBOX_BUTTON_RS),
        }
        
        # D-pad değerlerini al (Xbox 360'ta hat olarak temsil edilir)
        hat = self.controller.get_hat(0)
        buttons['UP'] = hat[1] > 0
        buttons['DOWN'] = hat[1] < 0
        buttons['LEFT'] = hat[0] < 0
        buttons['RIGHT'] = hat[0] > 0
        
        # Analog çubuk değerlerini al ve -32767 ile 32767 arasında normalize et
        l_stick_x = int(self.controller.get_axis(0) * 32767)
        l_stick_y = int(self.controller.get_axis(1) * -32767)  # Y-ekseni ters çevrildi
        r_stick_x = int(self.controller.get_axis(2) * 32767)
        r_stick_y = int(self.controller.get_axis(3) * -32767)  # Y-ekseni ters çevrildi
        
        return buttons, (l_stick_x, l_stick_y), (r_stick_x, r_stick_y)
    
    def create_switch_report(self, buttons, l_stick, r_stick):
        # Pro Controller rapor formatını oluştur
        report = bytearray(self.PACKET_SIZE)
        
        # Input report ID
        report[0] = 0x30  # Controller State report
        
        # Düğme durumlarını ayarla (3-5 baytları)
        if buttons['Y']: report[3] |= 0x01
        if buttons['X']: report[3] |= 0x02
        if buttons['B']: report[3] |= 0x04
        if buttons['A']: report[3] |= 0x08
        if buttons['R']: report[3] |= 0x40
        if buttons['ZR']: report[3] |= 0x80
        
        if buttons['MINUS']: report[4] |= 0x01
        if buttons['PLUS']: report[4] |= 0x02
        if buttons['RS']: report[4] |= 0x04
        if buttons['LS']: report[4] |= 0x08
        if buttons['HOME']: report[4] |= 0x10
        if buttons['CAPTURE']: report[4] |= 0x20
        
        if buttons['DOWN']: report[5] |= 0x01
        if buttons['UP']: report[5] |= 0x02
        if buttons['RIGHT']: report[5] |= 0x04
        if buttons['LEFT']: report[5] |= 0x08
        if buttons['L']: report[5] |= 0x40
        if buttons['ZL']: report[5] |= 0x80
        
        # Analog çubuk değerlerini ayarla (6-11 baytları)
        # Switch Pro Controller formatına dönüştür
        # Not: Bu değerleri Switch'in beklediği formata dönüştürmek için
        # daha fazla çalışma gerekebilir
        
        # Sol analog çubuk
        l_x = (l_stick[0] + 32767) >> 8  # 0-255 aralığına dönüştür
        l_y = (l_stick[1] + 32767) >> 8
        report[6] = l_x & 0xFF
        report[7] = (l_x >> 8) & 0x0F | ((l_y & 0x0F) << 4)
        report[8] = (l_y >> 4) & 0xFF
        
        # Sağ analog çubuk
        r_x = (r_stick[0] + 32767) >> 8
        r_y = (r_stick[1] + 32767) >> 8
        report[9] = r_x & 0xFF
        report[10] = (r_x >> 8) & 0x0F | ((r_y & 0x0F) << 4)
        report[11] = (r_y >> 4) & 0xFF
        
        return report
    
    def send_report(self, report):
        if self.gadget_mode:
            # Raspberry Pi'de USB üzerinden rapor gönder
            try:
                with open("/dev/hidg0", "wb") as f:
                    f.write(report)
            except Exception as e:
                print(f"Rapor gönderirken hata: {e}")
        else:
            # Windows veya USB gadget modu olmayan Linux'ta
            # Sadece raporu ekrana yazdır (debug için)
            hex_report = ' '.join([f'{b:02x}' for b in report[:16]])
            print(f"[DEBUG] Rapor: {hex_report}...")
    
    def start(self):
        self.running = True
        print("Pro Controller emülasyonu başladı")
        print("Çıkış için Ctrl+C tuşlarına basın")
        
        try:
            while self.running:
                # Xbox kontrolcüsünden veri oku
                buttons, l_stick, r_stick = self.xbox_to_switch_buttons()
                
                # Switch Pro Controller raporu oluştur
                report = self.create_switch_report(buttons, l_stick, r_stick)
                
                # Raporu gönder
                self.send_report(report)
                
                # Düğme durumlarını yazdır (debug için)
                pressed = [k for k, v in buttons.items() if v]
                if pressed:
                    print(f"Basılan düğmeler: {', '.join(pressed)}")
                
                time.sleep(0.01)  # 10ms bekleyerek işlemciyi rahatlat
                
        except KeyboardInterrupt:
            print("\nPro Controller emülasyonu durduruldu")
        finally:
            self.stop()
    
    def stop(self):
        self.running = False
        pygame.quit()
        
        # USB gadget modunu temizle
        if self.gadget_mode:
            try:
                gadget_dir = "/sys/kernel/config/usb_gadget/switchpro"
                with open(f"{gadget_dir}/UDC", "w") as f:
                    f.write("")
                os.unlink(f"{gadget_dir}/configs/c.1/hid.usb0")
                os.rmdir(f"{gadget_dir}/configs/c.1/strings/0x409")
                os.rmdir(f"{gadget_dir}/configs/c.1")
                os.rmdir(f"{gadget_dir}/functions/hid.usb0")
                os.rmdir(f"{gadget_dir}/strings/0x409")
                os.rmdir(gadget_dir)
                print("USB gadget temizlendi")
            except Exception as e:
                print(f"USB gadget temizlenirken hata: {e}")

if __name__ == "__main__":
    emulator = SwitchProEmulator()
    emulator.start()
