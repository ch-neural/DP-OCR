#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元件測試腳本
用於測試閱讀機器人的各個元件是否正常運作
"""

import sys
import time
import os


def test_gpio():
    """測試 GPIO"""
    print("測試 GPIO...", end=" ", flush=True)
    
    import RPi.GPIO as GPIO
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    state = GPIO.input(17)
    GPIO.cleanup()
    print(f"✓ (當前狀態: {'HIGH' if state else 'LOW'})")
    return True


def test_camera():
    """測試攝影機"""
    print("測試攝影機...", end=" ", flush=True)
    
    import cv2
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("✗ (無法開啟)")
        return False
    
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        print(f"✓ (解析度: {frame.shape[1]}x{frame.shape[0]})")
        return True
    else:
        print("✗ (無法讀取)")
        return False


def test_api():
    """測試 API 連線"""
    print("測試 API...", end=" ", flush=True)
    
    import requests
    import configparser
    
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        print("✗ (找不到 config.ini)")
        return False
    
    config.read('config.ini')
    api_url = config.get('API', 'api_url').rstrip('/')
    
    response = requests.get(f"{api_url}/health", timeout=5)
    
    if response.status_code == 200:
        print(f"✓ ({api_url})")
        return True
    else:
        print(f"✗ (HTTP {response.status_code})")
        return False


def test_audio():
    """測試音訊"""
    print("測試音訊...", end=" ", flush=True)
    
    import pygame
    
    pygame.mixer.init()
    
    sound_file = 'voices/看完了1.mp3'
    if not os.path.exists(sound_file):
        print(f"✗ (找不到音檔: {sound_file})")
        pygame.mixer.quit()
        return False
    
    pygame.mixer.music.load(sound_file)
    print("✓")
    pygame.mixer.quit()
    return True


def main():
    """主函數"""
    print("\n" + "=" * 50)
    print("閱讀機器人元件測試")
    print("=" * 50 + "\n")
    
    tests = [
        ("GPIO", test_gpio),
        ("攝影機", test_camera),
        ("API 連線", test_api),
        ("音訊系統", test_audio)
    ]
    
    results = []
    
    for name, test_func in tests:
        result = test_func()
        results.append(result)
        time.sleep(0.5)
    
    print("\n" + "=" * 50)
    print(f"測試結果: {sum(results)}/{len(results)} 通過")
    print("=" * 50 + "\n")
    
    if all(results):
        print("✓ 所有測試通過，系統正常")
        return 0
    else:
        print("✗ 有測試失敗，請檢查錯誤訊息")
        print("  詳細說明請參考: README/TROUBLESHOOTING.md")
        return 1


if __name__ == '__main__':
    sys.exit(main())

