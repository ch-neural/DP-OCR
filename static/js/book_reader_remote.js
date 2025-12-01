/**
 * Book Reader Remote - 客戶端 Webcam OCR
 * 使用者可以用自己電腦的 webcam 拍攝照片並上傳進行 OCR
 */

// 全域變數
let webcamStream = null;
let currentMode = 'webcam';  // 'webcam' 或 'upload'
let currentFrame = null;
let isProcessing = false;
let availableDevices = [];

// DOM 元素
const elements = {
    // Webcam 相關
    webcamVideo: null,
    webcamOverlay: null,
    webcamStatus: null,
    toggleWebcamBtn: null,
    cameraSelect: null,
    cameraResolution: null,
    mirrorMode: null,
    captureFlash: null,
    captureCanvas: null,
    
    // 上傳相關
    uploadArea: null,
    fileInput: null,
    uploadImage: null,
    uploadPreview: null,
    
    // 通用
    captureBtn: null,
    ocrPrompt: null,
    imageRotation: null,
    modelMaxSize: null,
    ocrResultArea: null,
    ocrResultContent: null,
    closeResultBtn: null,
    resultsHistory: null,
    loadingOverlay: null,
    capturedImageArea: null,
    capturedImage: null,
    clearResultsBtn: null
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initElements();
    initEventListeners();
    loadOCRResults();
    enumerateDevices();
});

// 初始化 DOM 元素引用
function initElements() {
    elements.webcamVideo = document.getElementById('webcam-video');
    elements.webcamOverlay = document.getElementById('webcam-overlay');
    elements.webcamStatus = document.getElementById('webcam-status');
    elements.toggleWebcamBtn = document.getElementById('toggle-webcam-btn');
    elements.cameraSelect = document.getElementById('camera-select');
    elements.cameraResolution = document.getElementById('camera-resolution');
    elements.mirrorMode = document.getElementById('mirror-mode');
    elements.captureFlash = document.getElementById('capture-flash');
    elements.captureCanvas = document.getElementById('capture-canvas');
    
    elements.uploadArea = document.getElementById('upload-area');
    elements.fileInput = document.getElementById('file-input');
    elements.uploadImage = document.getElementById('upload-image');
    elements.uploadPreview = document.getElementById('upload-preview');
    
    elements.captureBtn = document.getElementById('capture-btn');
    elements.ocrPrompt = document.getElementById('ocr-prompt');
    elements.imageRotation = document.getElementById('image-rotation');
    elements.modelMaxSize = document.getElementById('model-max-size');
    elements.ocrResultArea = document.getElementById('ocr-result-area');
    elements.ocrResultContent = document.getElementById('ocr-result-content');
    elements.closeResultBtn = document.getElementById('close-result-btn');
    elements.resultsHistory = document.getElementById('results-history');
    elements.loadingOverlay = document.getElementById('loading-overlay');
    elements.capturedImageArea = document.getElementById('captured-image-area');
    elements.capturedImage = document.getElementById('captured-image');
    elements.clearResultsBtn = document.getElementById('clear-results-btn');
}

// 初始化事件監聽器
function initEventListeners() {
    // Webcam 開關
    elements.toggleWebcamBtn.addEventListener('click', toggleWebcam);
    
    // 相機選擇
    elements.cameraSelect.addEventListener('change', handleCameraChange);
    
    // 解析度變更
    elements.cameraResolution.addEventListener('change', handleResolutionChange);
    
    // 鏡像模式
    elements.mirrorMode.addEventListener('change', handleMirrorChange);
    
    // 拍攝按鈕
    elements.captureBtn.addEventListener('click', handleCapture);
    
    // 清除結果
    elements.clearResultsBtn.addEventListener('click', handleClearResults);
    
    // 關閉結果
    elements.closeResultBtn.addEventListener('click', function() {
        elements.ocrResultArea.style.display = 'none';
    });
    
    // 上傳區域
    elements.uploadArea.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', handleFileSelect);
    
    // 拖放
    elements.uploadArea.addEventListener('dragover', handleDragOver);
    elements.uploadArea.addEventListener('dragleave', handleDragLeave);
    elements.uploadArea.addEventListener('drop', handleDrop);
}

// 列舉可用的攝影機設備
async function enumerateDevices() {
    try {
        // 先請求權限（某些瀏覽器需要）
        const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
        tempStream.getTracks().forEach(track => track.stop());
        
        const devices = await navigator.mediaDevices.enumerateDevices();
        availableDevices = devices.filter(device => device.kind === 'videoinput');
        
        // 更新下拉選單
        elements.cameraSelect.innerHTML = '';
        
        if (availableDevices.length === 0) {
            elements.cameraSelect.innerHTML = '<option value="">未偵測到攝影機</option>';
            return;
        }
        
        availableDevices.forEach((device, index) => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.textContent = device.label || `攝影機 ${index + 1}`;
            elements.cameraSelect.appendChild(option);
        });
        
        console.log(`偵測到 ${availableDevices.length} 個攝影機設備`);
    } catch (error) {
        console.error('列舉設備失敗:', error);
        elements.cameraSelect.innerHTML = '<option value="">無法存取攝影機</option>';
        updateWebcamStatus('error', '無法存取攝影機：' + error.message);
    }
}

// 切換 Webcam 開關
async function toggleWebcam() {
    if (webcamStream) {
        stopWebcam();
    } else {
        await startWebcam();
    }
}

// 開啟 Webcam
async function startWebcam() {
    updateWebcamStatus('connecting', '正在連接...');
    
    const deviceId = elements.cameraSelect.value;
    const resolution = elements.cameraResolution.value.split('x');
    
    const constraints = {
        video: {
            width: { ideal: parseInt(resolution[0]) },
            height: { ideal: parseInt(resolution[1]) },
            facingMode: 'user'  // 預設使用前置鏡頭
        },
        audio: false
    };
    
    // 如果有選擇特定設備
    if (deviceId) {
        constraints.video.deviceId = { exact: deviceId };
    }
    
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia(constraints);
        
        elements.webcamVideo.srcObject = webcamStream;
        
        // 等待影片載入
        await new Promise((resolve, reject) => {
            elements.webcamVideo.onloadedmetadata = resolve;
            elements.webcamVideo.onerror = reject;
        });
        
        await elements.webcamVideo.play();
        
        // 更新 UI
        elements.webcamOverlay.classList.add('hidden');
        elements.toggleWebcamBtn.textContent = '⏹️ 關閉 Webcam';
        elements.captureBtn.disabled = false;
        updateWebcamStatus('connected', `✅ 已連接 (${elements.webcamVideo.videoWidth}x${elements.webcamVideo.videoHeight})`);
        
        // 更新鏡像模式
        handleMirrorChange();
        
        console.log('Webcam 已開啟');
    } catch (error) {
        console.error('開啟 Webcam 失敗:', error);
        updateWebcamStatus('error', '❌ 連接失敗：' + getErrorMessage(error));
        elements.webcamOverlay.classList.remove('hidden');
        elements.webcamOverlay.innerHTML = `<p>❌ ${getErrorMessage(error)}</p>`;
    }
}

// 關閉 Webcam
function stopWebcam() {
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }
    
    elements.webcamVideo.srcObject = null;
    elements.webcamOverlay.classList.remove('hidden');
    elements.webcamOverlay.innerHTML = '<p>🎥 請點擊「開啟 Webcam」開始</p>';
    elements.toggleWebcamBtn.textContent = '🎥 開啟 Webcam';
    
    if (currentMode === 'webcam') {
        elements.captureBtn.disabled = true;
    }
    
    updateWebcamStatus('disconnected', '⚫ 已關閉');
    console.log('Webcam 已關閉');
}

// 處理相機變更
async function handleCameraChange() {
    if (webcamStream) {
        stopWebcam();
        await startWebcam();
    }
}

// 處理解析度變更
async function handleResolutionChange() {
    if (webcamStream) {
        stopWebcam();
        await startWebcam();
    }
}

// 處理鏡像模式變更
function handleMirrorChange() {
    if (elements.mirrorMode.checked) {
        elements.webcamVideo.classList.remove('no-mirror');
    } else {
        elements.webcamVideo.classList.add('no-mirror');
    }
}

// 更新 Webcam 狀態顯示
function updateWebcamStatus(type, message) {
    elements.webcamStatus.className = 'webcam-status ' + type;
    elements.webcamStatus.textContent = message;
}

// 獲取錯誤訊息
function getErrorMessage(error) {
    if (error.name === 'NotAllowedError') {
        return '請允許瀏覽器存取攝影機';
    } else if (error.name === 'NotFoundError') {
        return '找不到攝影機設備';
    } else if (error.name === 'NotReadableError') {
        return '攝影機正被其他程式使用';
    } else if (error.name === 'OverconstrainedError') {
        return '攝影機不支援此解析度';
    }
    return error.message || '未知錯誤';
}

// 切換模式
function switchMode(mode) {
    currentMode = mode;
    
    // 更新 Tab 樣式
    document.querySelectorAll('.mode-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.getElementById('mode-' + mode).classList.add('active');
    
    // 更新內容顯示
    document.querySelectorAll('.mode-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(mode + '-mode').classList.add('active');
    document.getElementById(mode + '-settings')?.classList.add('active');
    
    // 更新拍攝按鈕狀態
    if (mode === 'webcam') {
        elements.captureBtn.disabled = !webcamStream;
        elements.captureBtn.textContent = '📸 拍攝 & OCR';
    } else {
        elements.captureBtn.disabled = !currentFrame;
        elements.captureBtn.textContent = '📤 上傳 & OCR';
    }
}

// 處理拍攝
async function handleCapture() {
    if (isProcessing) return;
    
    let imageBase64;
    
    if (currentMode === 'webcam') {
        // Webcam 模式：從影片擷取畫面
        if (!webcamStream) {
            alert('請先開啟 Webcam');
            return;
        }
        
        // 拍攝快閃效果
        showCaptureFlash();
        
        imageBase64 = captureFromVideo();
    } else {
        // 上傳模式：使用已上傳的圖片
        if (!currentFrame) {
            alert('請先選擇或上傳圖片');
            return;
        }
        imageBase64 = currentFrame;
    }
    
    if (!imageBase64) {
        alert('無法取得影像');
        return;
    }
    
    isProcessing = true;
    elements.captureBtn.disabled = true;
    
    try {
        showLoading('正在處理影像...');
        
        // 處理影像（旋轉和調整大小）
        const rotation = parseInt(elements.imageRotation.value) || 0;
        const maxSize = parseInt(elements.modelMaxSize.value) || 1024;
        const isMirrored = currentMode === 'webcam' && elements.mirrorMode.checked;
        
        const processedImage = await processImage(imageBase64, rotation, maxSize, isMirrored);
        
        // 顯示處理後的照片
        elements.capturedImage.src = 'data:image/jpeg;base64,' + processedImage;
        elements.capturedImageArea.style.display = 'block';
        elements.capturedImageArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        // 發送 OCR 請求
        showLoading('正在執行 OCR 辨識...');
        
        const userPrompt = elements.ocrPrompt.value.trim() || null;
        
        const response = await fetch('/api/ocr/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                frame: processedImage,
                prompt: userPrompt
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || 'OCR 處理失敗');
        }
        
        const result = await response.json();
        displayOCRResult(result);
        loadOCRResults();
        
    } catch (error) {
        console.error('處理錯誤:', error);
        alert('處理失敗: ' + error.message);
    } finally {
        isProcessing = false;
        elements.captureBtn.disabled = false;
        hideLoading();
    }
}

// 從影片擷取畫面
function captureFromVideo() {
    const video = elements.webcamVideo;
    const canvas = elements.captureCanvas;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    
    // 如果是鏡像模式，需要在擷取時翻轉
    if (elements.mirrorMode.checked) {
        ctx.translate(canvas.width, 0);
        ctx.scale(-1, 1);
    }
    
    ctx.drawImage(video, 0, 0);
    
    // 重置變換
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    
    // 轉換為 base64（不含前綴）
    const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
    return dataUrl.split(',')[1];
}

// 顯示拍攝快閃效果
function showCaptureFlash() {
    elements.captureFlash.classList.add('active');
    setTimeout(() => {
        elements.captureFlash.classList.remove('active');
    }, 150);
}

// 處理影像（旋轉和調整大小）
async function processImage(base64Image, rotation, maxSize, flipHorizontal = false) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = function() {
            const canvas = document.createElement('canvas');
            let ctx = canvas.getContext('2d');
            
            let width = img.width;
            let height = img.height;
            
            // 計算旋轉後的尺寸
            if (rotation === 90 || rotation === 270) {
                [width, height] = [height, width];
            }
            
            canvas.width = width;
            canvas.height = height;
            
            // 應用變換
            ctx.translate(width / 2, height / 2);
            ctx.rotate((rotation * Math.PI) / 180);
            
            if (flipHorizontal) {
                ctx.scale(-1, 1);
            }
            
            ctx.translate(-img.width / 2, -img.height / 2);
            ctx.drawImage(img, 0, 0);
            
            // 調整大小
            let finalWidth = width;
            let finalHeight = height;
            const maxDimension = Math.max(width, height);
            
            if (maxDimension > maxSize) {
                const scale = maxSize / maxDimension;
                finalWidth = Math.round(width * scale);
                finalHeight = Math.round(height * scale);
            }
            
            if (finalWidth !== width || finalHeight !== height) {
                const resizedCanvas = document.createElement('canvas');
                resizedCanvas.width = finalWidth;
                resizedCanvas.height = finalHeight;
                const resizedCtx = resizedCanvas.getContext('2d');
                resizedCtx.drawImage(canvas, 0, 0, width, height, 0, 0, finalWidth, finalHeight);
                
                resolve(resizedCanvas.toDataURL('image/jpeg', 0.95).split(',')[1]);
            } else {
                resolve(canvas.toDataURL('image/jpeg', 0.95).split(',')[1]);
            }
        };
        
        img.onerror = () => reject(new Error('圖片載入失敗'));
        img.src = 'data:image/jpeg;base64,' + base64Image;
    });
}

// 處理檔案選擇
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        loadImageFile(file);
    }
}

// 處理拖放
function handleDragOver(event) {
    event.preventDefault();
    elements.uploadArea.classList.add('dragover');
}

function handleDragLeave(event) {
    event.preventDefault();
    elements.uploadArea.classList.remove('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    elements.uploadArea.classList.remove('dragover');
    
    const file = event.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
        loadImageFile(file);
    }
}

// 載入圖片檔案
function loadImageFile(file) {
    const reader = new FileReader();
    
    reader.onload = function(e) {
        const base64 = e.target.result.split(',')[1];
        currentFrame = base64;
        
        elements.uploadImage.src = e.target.result;
        elements.uploadPreview.style.display = 'block';
        elements.captureBtn.disabled = false;
        
        console.log('圖片已載入:', file.name);
    };
    
    reader.readAsDataURL(file);
}

// 顯示 OCR 結果
function displayOCRResult(result) {
    elements.ocrResultArea.style.display = 'block';
    
    let content = '';
    
    if (result.status === 'completed') {
        const cleanText = filterSystemMessages(result.text || '');
        
        if (!cleanText || cleanText.trim().length === 0) {
            content = `
                <div class="result-success">✅ OCR 辨識成功！</div>
                <div class="result-warning" style="margin-top: 15px;">⚠️ OCR 結果為空</div>
            `;
        } else {
            content = `
                <div class="result-success">✅ OCR 辨識成功！</div>
                <div class="result-item-text" style="margin-top: 15px; white-space: pre-wrap; word-wrap: break-word;">${escapeHtml(cleanText)}</div>
            `;
        }
    } else if (result.status === 'skipped') {
        content = `
            <div class="result-warning">⚠️ 跳過 OCR</div>
            <p style="margin-top: 10px;">原因: ${escapeHtml(result.skip_reason || 'Unknown')}</p>
        `;
    } else {
        content = `
            <div class="result-error">❌ OCR 辨識失敗</div>
            <p style="margin-top: 10px;">錯誤: ${escapeHtml(result.error || 'Unknown error')}</p>
        `;
    }
    
    elements.ocrResultContent.innerHTML = content;
    elements.ocrResultArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// 過濾系統訊息
function filterSystemMessages(text) {
    if (!text) return '';
    
    const lines = text.split('\n');
    const filteredLines = [];
    
    const systemKeywords = [
        '開始模型推理',
        '模型推理完成',
        'OCR 推理執行成功',
        'BASE:',
        'PATCHES:'
    ];
    
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        
        let isSystem = false;
        for (const keyword of systemKeywords) {
            if (trimmed.startsWith(keyword)) {
                isSystem = true;
                break;
            }
        }
        
        if (!isSystem) {
            filteredLines.push(line);
        }
    }
    
    return filteredLines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

// 載入 OCR 結果歷史
async function loadOCRResults() {
    try {
        const response = await fetch('/api/ocr/results');
        const results = await response.json();
        
        if (results.length === 0) {
            elements.resultsHistory.innerHTML = `
                <div class="empty-state">
                    <p>尚無 OCR 結果</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        results.forEach(result => {
            html += createResultItemHTML(result);
        });
        
        elements.resultsHistory.innerHTML = html;
    } catch (error) {
        console.error('載入 OCR 結果失敗:', error);
    }
}

// 創建結果項目 HTML
function createResultItemHTML(result) {
    let statusClass = '';
    let statusText = '';
    
    if (result.status === 'completed') {
        statusClass = 'status-completed';
        statusText = '成功';
    } else if (result.status === 'error') {
        statusClass = 'status-error';
        statusText = '失敗';
    } else if (result.status === 'skipped') {
        statusClass = 'status-skipped';
        statusText = '跳過';
    }
    
    let imageHTML = '';
    if (result.image_url) {
        imageHTML = `<img src="${result.image_url}" alt="圖片" class="result-item-image" onerror="this.style.display='none'">`;
    }
    
    let contentHTML = '';
    if (result.status === 'completed' && result.text) {
        const cleanText = filterSystemMessages(result.text);
        contentHTML = `<div class="result-item-text" style="white-space: pre-wrap; word-wrap: break-word;">${escapeHtml(cleanText)}</div>`;
    } else if (result.status === 'skipped') {
        contentHTML = `<p class="result-warning">跳過原因: ${escapeHtml(result.skip_reason || 'Unknown')}</p>`;
    } else if (result.status === 'error') {
        contentHTML = `<p class="result-error">錯誤: ${escapeHtml(result.error || 'Unknown error')}</p>`;
    }
    
    return `
        <div class="result-item">
            <div class="result-item-header">
                <div class="result-item-title">📄 ${result.datetime || result.id || 'Unknown'}</div>
                <span class="result-item-status ${statusClass}">${statusText}</span>
            </div>
            ${imageHTML}
            ${contentHTML}
            <div class="result-item-meta">ID: ${result.id || 'Unknown'} | 時間: ${result.datetime || 'Unknown'}</div>
        </div>
    `;
}

// 處理清除結果
async function handleClearResults() {
    if (!confirm('確定要清除所有 OCR 結果嗎？')) return;
    
    try {
        const response = await fetch('/api/ocr/results/clear', { method: 'POST' });
        if (response.ok) {
            loadOCRResults();
            alert('所有結果已清除');
        } else {
            alert('清除失敗');
        }
    } catch (error) {
        console.error('清除結果錯誤:', error);
        alert('清除失敗: ' + error.message);
    }
}

// 顯示/隱藏載入指示器
function showLoading(text = '處理中...') {
    const loadingText = elements.loadingOverlay.querySelector('.loading-text');
    if (loadingText) loadingText.textContent = text;
    elements.loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    elements.loadingOverlay.style.display = 'none';
}

// HTML 轉義
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 頁面卸載時清理
window.addEventListener('beforeunload', function() {
    stopWebcam();
});

// 讓 switchMode 函數可以從 HTML 調用
window.switchMode = switchMode;

