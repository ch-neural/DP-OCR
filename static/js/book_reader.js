// Book Reader Flask - JavaScript

let cameraEventSource = null;
let isProcessing = false;
let currentFrame = null;

// DOM 元素
const elements = {
    enablePreview: document.getElementById('enable-preview'),
    cameraSelect: document.getElementById('camera-select'),
    cameraDevice: document.getElementById('camera-device'),
    refreshCamerasBtn: document.getElementById('refresh-cameras-btn'),
    cameraPreview: document.getElementById('camera-preview'),
    cameraError: document.getElementById('camera-error'),
    captureBtn: document.getElementById('capture-btn'),
    resetCameraBtn: document.getElementById('reset-camera-btn'),
    clearResultsBtn: document.getElementById('clear-results-btn'),
    ocrPrompt: document.getElementById('ocr-prompt'),
    ocrResultArea: document.getElementById('ocr-result-area'),
    ocrResultContent: document.getElementById('ocr-result-content'),
    closeResultBtn: document.getElementById('close-result-btn'),
    resultsHistory: document.getElementById('results-history'),
    loadingOverlay: document.getElementById('loading-overlay'),
    capturedImageArea: document.getElementById('captured-image-area'),
    capturedImage: document.getElementById('captured-image'),
    cameraResolution: document.getElementById('camera-resolution'),
    imageRotation: document.getElementById('image-rotation'),
    modelMaxSize: document.getElementById('model-max-size'),
    previewContainer: null  // 將在初始化時設置
};

// 當前選擇的相機 ID
let currentCameraId = null;

// 當前應用的旋轉角度（用於避免重複處理）
let currentAppliedRotation = null;

// 防抖計時器
let rotationUpdateTimer = null;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadOCRResults();
    
    // 初始化預覽容器引用
    if (elements.cameraPreview) {
        elements.previewContainer = elements.cameraPreview.parentElement;
        console.log('預覽容器已找到:', elements.previewContainer);
    }
    
    // 初始化相機選擇
    if (elements.cameraSelect) {
        const selectedValue = elements.cameraSelect.value;
        currentCameraId = selectedValue ? parseInt(selectedValue) : 0;
        if (isNaN(currentCameraId)) {
            currentCameraId = 0;
        }
        console.log('初始化相機 ID:', currentCameraId);
        updateCameraDeviceDisplay();
    }
    
    // 如果啟用預覽，開始串流
    if (elements.enablePreview.checked) {
        startCameraStream();
    }
    
    // 初始化預覽旋轉角度
    if (elements.imageRotation) {
        const initialRotation = parseInt(elements.imageRotation.value) || 0;
        currentAppliedRotation = initialRotation;
        updatePreviewRotation(initialRotation);
    }
});

// 事件監聽器
function initializeEventListeners() {
    // 啟用/停用預覽
    elements.enablePreview.addEventListener('change', function() {
        if (this.checked) {
            startCameraStream();
        } else {
            stopCameraStream();
        }
    });
    
    // 相機選擇變更
    if (elements.cameraSelect) {
        elements.cameraSelect.addEventListener('change', async function() {
            const newCameraId = parseInt(this.value);
            await handleCameraChange(newCameraId);
        });
    }
    
    // 相機解析度變更
    if (elements.cameraResolution) {
        elements.cameraResolution.addEventListener('change', async function() {
            const resolution = this.value;
            console.log('相機解析度變更為:', resolution);
            // 如果預覽已啟用，重新啟動串流以應用新解析度
            if (elements.enablePreview.checked) {
                stopCameraStream();
                await new Promise(resolve => setTimeout(resolve, 300));
                await updateCameraResolution(resolution);
                startCameraStream();
            }
        });
    }
    
    // 影像旋轉角度變更
    if (elements.imageRotation) {
        elements.imageRotation.addEventListener('change', function() {
            const rotation = parseInt(this.value) || 0;
            console.log('影像旋轉角度變更為:', rotation);
            console.log('cameraPreview 元素:', elements.cameraPreview);
            console.log('cameraPreview 當前樣式:', elements.cameraPreview ? window.getComputedStyle(elements.cameraPreview).transform : 'N/A');
            updatePreviewRotation(rotation);
            console.log('cameraPreview 更新後樣式:', elements.cameraPreview ? window.getComputedStyle(elements.cameraPreview).transform : 'N/A');
        });
    } else {
        console.warn('imageRotation 元素未找到');
    }
    
    // 重新偵測相機
    if (elements.refreshCamerasBtn) {
        elements.refreshCamerasBtn.addEventListener('click', handleRefreshCameras);
    }
    
    // 拍攝 & OCR
    elements.captureBtn.addEventListener('click', handleCapture);
    
    // 重置相機
    elements.resetCameraBtn.addEventListener('click', handleResetCamera);
    
    // 清除結果
    elements.clearResultsBtn.addEventListener('click', handleClearResults);
    
    // 關閉結果
    elements.closeResultBtn.addEventListener('click', function() {
        elements.ocrResultArea.style.display = 'none';
    });
}

// 開始相機串流
function startCameraStream() {
    // 確保先停止舊的串流
    if (cameraEventSource) {
        stopCameraStream();
        // 等待舊串流完全關閉
        setTimeout(() => {
            _startCameraStreamInternal();
        }, 200);
    } else {
        _startCameraStreamInternal();
    }
}

// 內部函數：實際開始串流
function _startCameraStreamInternal() {
    // 確保 currentCameraId 是有效的數字
    if (currentCameraId === null || isNaN(currentCameraId)) {
        currentCameraId = 0;
        console.warn('currentCameraId 無效，使用預設值 0');
    }
    
    // 構建 URL，包含相機 ID 參數和時間戳（避免緩存）
    let streamUrl = '/api/camera/stream';
    streamUrl += `?camera_id=${currentCameraId}`;
    streamUrl += `&t=${Date.now()}`; // 添加時間戳避免緩存
    
    console.log('開始相機串流:', streamUrl, 'currentCameraId =', currentCameraId);
    window._frameReceived = false; // 重置畫面接收標記
    
    cameraEventSource = new EventSource(streamUrl);
    
    cameraEventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        if (data.frame) {
            // 只在旋轉角度改變時才更新（避免每次收到畫面都重複處理）
            const rotation = elements.imageRotation ? parseInt(elements.imageRotation.value) || 0 : 0;
            if (currentAppliedRotation !== rotation) {
                updatePreviewRotation(rotation);
            }
            
            elements.cameraPreview.src = 'data:image/jpeg;base64,' + data.frame;
            elements.cameraPreview.style.display = 'block';
            elements.cameraError.style.display = 'none';
            currentFrame = data.frame; // 保存當前畫面
            
            // 只在首次收到畫面時記錄
            if (!window._frameReceived) {
                console.log('✅ 相機串流畫面已接收，currentFrame 已設置');
                window._frameReceived = true;
            }
        } else if (data.error) {
            console.warn('相機串流錯誤:', data.error);
            elements.cameraPreview.style.display = 'none';
            elements.cameraError.style.display = 'block';
            // 更新錯誤訊息
            const errorDetails = elements.cameraError.querySelector('.error-details');
            if (errorDetails) {
                errorDetails.textContent = data.error;
            }
            currentFrame = null;
            window._frameReceived = false;
        }
    };
    
    cameraEventSource.onerror = function(error) {
        console.error('相機串流連接錯誤:', error);
        // 不立即停止，給一些時間重連
        elements.cameraPreview.style.display = 'none';
        elements.cameraError.style.display = 'block';
        // 如果錯誤持續，3秒後停止並重試
        setTimeout(() => {
            if (cameraEventSource && cameraEventSource.readyState === EventSource.CLOSED) {
                console.log('串流已關閉，嘗試重新連接...');
                stopCameraStream();
                if (elements.enablePreview.checked) {
                    setTimeout(() => {
                        startCameraStream();
                    }, 1000);
                }
            }
        }, 3000);
    };
    
    // 串流打開成功
    cameraEventSource.onopen = function() {
        console.log('相機串流已連接');
    };
}

// 停止相機串流
function stopCameraStream() {
    if (cameraEventSource) {
        cameraEventSource.close();
        cameraEventSource = null;
    }
    // 不要隱藏預覽畫面，保留最後一幀畫面
    // 只清除 currentFrame，防止使用過期的畫面進行 OCR
    currentFrame = null;
}

// 處理影像旋轉和 resize（在 Canvas 上處理）
async function processImage(base64Image, rotation, maxSize) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = function() {
            const canvas = document.createElement('canvas');
            let ctx = canvas.getContext('2d');
            
            // 計算旋轉後的尺寸
            let width = img.width;
            let height = img.height;
            
            // 應用旋轉
            if (rotation === 90 || rotation === 270) {
                // 90度或270度旋轉時，寬高互換
                [width, height] = [height, width];
            }
            
            canvas.width = width;
            canvas.height = height;
            
            // 旋轉畫布
            ctx.translate(width / 2, height / 2);
            ctx.rotate((rotation * Math.PI) / 180);
            ctx.translate(-img.width / 2, -img.height / 2);
            
            // 繪製圖片
            ctx.drawImage(img, 0, 0);
            
            // 計算 resize 後的尺寸（等比例，以長邊為準）
            let finalWidth = width;
            let finalHeight = height;
            const maxDimension = Math.max(width, height);
            
            if (maxDimension > maxSize) {
                const scale = maxSize / maxDimension;
                finalWidth = Math.round(width * scale);
                finalHeight = Math.round(height * scale);
            }
            
            // 如果尺寸有變化，創建新的 canvas 進行 resize
            if (finalWidth !== width || finalHeight !== height) {
                const resizedCanvas = document.createElement('canvas');
                resizedCanvas.width = finalWidth;
                resizedCanvas.height = finalHeight;
                const resizedCtx = resizedCanvas.getContext('2d');
                resizedCtx.drawImage(canvas, 0, 0, width, height, 0, 0, finalWidth, finalHeight);
                canvas.width = finalWidth;
                canvas.height = finalHeight;
                ctx = canvas.getContext('2d');
                ctx.drawImage(resizedCanvas, 0, 0);
            }
            
            // 轉換為 base64
            const processedBase64 = canvas.toDataURL('image/jpeg', 0.95).split(',')[1];
            resolve(processedBase64);
        };
        
        img.onerror = function() {
            reject(new Error('圖片載入失敗'));
        };
        
        img.src = 'data:image/jpeg;base64,' + base64Image;
    });
}

// 處理拍攝
async function handleCapture() {
    if (isProcessing) {
        return;
    }
    
    // 檢查是否有可用的畫面
    console.log('handleCapture: currentFrame =', currentFrame ? '存在' : '不存在');
    console.log('handleCapture: cameraEventSource =', cameraEventSource ? '存在' : '不存在');
    console.log('handleCapture: enablePreview.checked =', elements.enablePreview.checked);
    
    if (!currentFrame) {
        const errorMsg = '無法拍攝：相機畫面不可用\n\n' +
            '可能的原因：\n' +
            '1. 相機預覽未啟用（請勾選「啟用相機預覽」）\n' +
            '2. 相機串流未連接\n' +
            '3. 相機設備異常\n\n' +
            '請確認相機已連接且預覽已啟用後再試';
        alert(errorMsg);
        return;
    }
    
    isProcessing = true;
    elements.captureBtn.disabled = true;
    
    try {
        // 步驟 1: 使用當前串流的畫面（避免相機資源衝突）
        const capturedFrameBase64 = currentFrame;
        console.log('handleCapture: 使用 currentFrame，長度 =', capturedFrameBase64 ? capturedFrameBase64.length : 0);
        showLoading('正在處理影像...');
        
        // 步驟 2: 處理影像（旋轉和 resize）
        const rotation = parseInt(elements.imageRotation.value) || 0;
        const maxSize = parseInt(elements.modelMaxSize.value) || 1024;
        
        console.log('處理參數: rotation =', rotation, 'maxSize =', maxSize);
        console.log('原始圖片 base64 長度:', capturedFrameBase64.length);
        
        const processedFrameBase64 = await processImage(capturedFrameBase64, rotation, maxSize);
        console.log('處理後圖片 base64 長度:', processedFrameBase64.length);
        
        // 步驟 3: 立即顯示處理後的照片
        elements.capturedImage.src = 'data:image/jpeg;base64,' + processedFrameBase64;
        elements.capturedImageArea.style.display = 'block';
        
        // 滾動到拍攝照片區域
        elements.capturedImageArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        // 步驟 4: 提交 OCR 請求
        showLoading('正在執行 OCR 辨識...');
        
        // 獲取使用者輸入的 prompt
        // 如果為空，後端會使用預設 prompt（從 config.ini 讀取）
        const userPrompt = elements.ocrPrompt.value.trim();
        
        // 發送 OCR 請求（使用處理後的影像）
        // prompt 會附加到每次 OCR 請求中，傳遞給 DeepSeek-OCR API
        const ocrResponse = await fetch('/api/ocr/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                frame: processedFrameBase64,
                prompt: userPrompt  // 空字串時後端會使用預設 prompt
            })
        });
        
        if (!ocrResponse.ok) {
            const errorData = await ocrResponse.json().catch(() => ({}));
            throw new Error(errorData.error || 'OCR 處理失敗');
        }
        
        const result = await ocrResponse.json();
        
        // 詳細日誌：記錄 OCR 結果
        console.log('OCR API 回應狀態碼:', ocrResponse.status);
        console.log('OCR API 回應結果:', result);
        console.log('OCR 結果狀態:', result.status);
        console.log('OCR 結果文字長度:', result.text ? result.text.length : 0);
        console.log('OCR 結果文字前 200 字元:', result.text ? result.text.substring(0, 200) : '(無文字)');
        
        // 顯示 OCR 結果
        displayOCRResult(result);
        
        // 重新載入歷史記錄
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

// 過濾 OCR 文字中的系統訊息
function filterSystemMessages(text) {
    if (!text) return '';
    
    // 按行分割文字
    const lines = text.split('\n');
    const filteredLines = [];
    
    // 定義要過濾的系統訊息關鍵字（必須是完整的行）
    const systemMessageKeywords = [
        '開始模型推理',
        '模型推理完成',
        'OCR 推理執行成功',
        'BASE:',
        'PATCHES:'
    ];
    
    // 過濾每一行
    for (const line of lines) {
        const trimmedLine = line.trim();
        // 跳過空行
        if (!trimmedLine) {
            // 保留空行（但會稍後清理多餘的）
            continue;
        }
        
        // 檢查是否為系統訊息（必須完全匹配或行首匹配）
        let isSystemMessage = false;
        for (const keyword of systemMessageKeywords) {
            // 檢查是否以關鍵字開頭（允許後面有其他文字，如 "開始模型推理 (超時: 300 秒)..."）
            if (trimmedLine.startsWith(keyword)) {
                isSystemMessage = true;
                break;
            }
        }
        
        // 如果不是系統訊息，保留這一行
        if (!isSystemMessage) {
            filteredLines.push(line);
        }
    }
    
    // 重新組合文字
    let filteredText = filteredLines.join('\n');
    
    // 清理多餘的換行（連續的換行變成單個換行，但保留段落間的空行）
    filteredText = filteredText.replace(/\n{3,}/g, '\n\n');
    
    // 移除開頭和結尾的空白
    return filteredText.trim();
}

// 顯示 OCR 結果
function displayOCRResult(result) {
    console.log('displayOCRResult: result =', result);
    console.log('displayOCRResult: result.status =', result.status);
    console.log('displayOCRResult: result.text =', result.text);
    console.log('displayOCRResult: result.text type =', typeof result.text);
    console.log('displayOCRResult: result.text length =', result.text ? result.text.length : 0);
    
    elements.ocrResultArea.style.display = 'block';
    
    let content = '';
    
    if (result.status === 'completed') {
        // 檢查 result.text 是否存在
        if (!result.text) {
            console.warn('displayOCRResult: result.text 不存在或為空');
            content = `
                <div class="result-success">✅ OCR 辨識成功！</div>
                <div class="result-warning" style="margin-top: 15px;">⚠️ OCR 結果為空</div>
            `;
        } else {
            // 過濾掉系統訊息，只保留 OCR 內容
            const cleanText = filterSystemMessages(result.text);
            console.log('displayOCRResult: cleanText =', cleanText);
            console.log('displayOCRResult: cleanText length =', cleanText.length);
            
            if (!cleanText || cleanText.trim().length === 0) {
                console.warn('displayOCRResult: 過濾後文字為空');
                content = `
                    <div class="result-success">✅ OCR 辨識成功！</div>
                    <div class="result-warning" style="margin-top: 15px;">⚠️ OCR 結果在過濾後為空（可能只包含系統訊息）</div>
                    <div class="result-item-text" style="margin-top: 15px; white-space: pre-wrap; word-wrap: break-word; color: #999; font-style: italic;">原始文字: ${escapeHtml(result.text)}</div>
                `;
            } else {
                content = `
                    <div class="result-success">✅ OCR 辨識成功！</div>
                    <div class="result-item-text" style="margin-top: 15px; white-space: pre-wrap; word-wrap: break-word;">${escapeHtml(cleanText)}</div>
                `;
            }
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
    
    console.log('displayOCRResult: content =', content);
    elements.ocrResultContent.innerHTML = content;
    
    // 滾動到結果區域
    elements.ocrResultArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
        results.forEach((result, index) => {
            html += createResultItemHTML(result, index);
        });
        
        elements.resultsHistory.innerHTML = html;
        
    } catch (error) {
        console.error('載入 OCR 結果失敗:', error);
    }
}

// 創建結果項目 HTML
function createResultItemHTML(result, index) {
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
        // 使用 image_url（如果可用）
        imageHTML = `<img src="${result.image_url}" alt="拍攝圖片" class="result-item-image" onerror="this.style.display='none'">`;
    } else if (result.image_path) {
        // 嘗試載入圖片（如果路徑可用）
        imageHTML = `<img src="/static/${result.image_path}" alt="拍攝圖片" class="result-item-image" onerror="this.style.display='none'">`;
    }
    
    let contentHTML = '';
    if (result.status === 'completed' && result.text) {
        // 過濾掉系統訊息，只保留 OCR 內容
        const cleanText = filterSystemMessages(result.text);
        contentHTML = `
            <div class="result-item-text" style="white-space: pre-wrap; word-wrap: break-word;">${escapeHtml(cleanText)}</div>
        `;
    } else if (result.status === 'skipped') {
        contentHTML = `
            <p class="result-warning">跳過原因: ${escapeHtml(result.skip_reason || 'Unknown')}</p>
        `;
    } else if (result.status === 'error') {
        contentHTML = `
            <p class="result-error">錯誤: ${escapeHtml(result.error || 'Unknown error')}</p>
        `;
    }
    
    return `
        <div class="result-item">
            <div class="result-item-header">
                <div class="result-item-title">
                    📄 ${result.datetime || result.id || 'Unknown'}
                </div>
                <span class="result-item-status ${statusClass}">${statusText}</span>
            </div>
            ${imageHTML}
            ${contentHTML}
            <div class="result-item-meta">
                ID: ${result.id || 'Unknown'} | 時間: ${result.datetime || 'Unknown'}
            </div>
        </div>
    `;
}

// 處理相機變更
async function handleCameraChange(newCameraId) {
    if (isProcessing) {
        return;
    }
    
    if (newCameraId === currentCameraId) {
        return; // 沒有變更
    }
    
    // 先停止舊的串流，確保資源釋放
    const wasPreviewEnabled = elements.enablePreview.checked;
    if (wasPreviewEnabled) {
        stopCameraStream();
        // 等待串流完全停止
        await new Promise(resolve => setTimeout(resolve, 300));
    }
    
    // 設定相機設備
    try {
        const response = await fetch('/api/camera/set', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                device_id: newCameraId
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentCameraId = newCameraId;
            updateCameraDeviceDisplay();
            
            // 如果預覽已啟用，等待資源釋放後重新開始串流
            if (wasPreviewEnabled) {
                // 等待更長時間，確保相機資源完全釋放
                await new Promise(resolve => setTimeout(resolve, 800));
                startCameraStream();
            }
        } else {
            alert('切換相機失敗: ' + (result.error || 'Unknown error'));
            // 恢復選擇
            elements.cameraSelect.value = currentCameraId;
            // 如果之前有預覽，嘗試恢復
            if (wasPreviewEnabled) {
                setTimeout(() => {
                    startCameraStream();
                }, 500);
            }
        }
    } catch (error) {
        console.error('切換相機錯誤:', error);
        alert('切換相機失敗: ' + error.message);
        // 恢復選擇
        elements.cameraSelect.value = currentCameraId;
        // 如果之前有預覽，嘗試恢復
        if (wasPreviewEnabled) {
            setTimeout(() => {
                startCameraStream();
            }, 500);
        }
    }
}

// 處理重新偵測相機
async function handleRefreshCameras() {
    if (isProcessing) {
        return;
    }
    
    try {
        const response = await fetch('/api/camera/list');
        const data = await response.json();
        
        // 更新下拉選單
        const select = elements.cameraSelect;
        const currentValue = select.value;
        
        // 清空選項
        select.innerHTML = '';
        
        // 添加新選項
        data.cameras.forEach(camera => {
            const option = document.createElement('option');
            option.value = camera.id;
            option.textContent = `${camera.name} (${camera.device_path})`;
            if (camera.id === data.current_camera_id) {
                option.selected = true;
                currentCameraId = camera.id;
            }
            select.appendChild(option);
        });
        
        updateCameraDeviceDisplay();
        
        // 如果預覽已啟用，重新開始串流
        if (elements.enablePreview.checked) {
            stopCameraStream();
            setTimeout(() => {
                startCameraStream();
            }, 500);
        }
        
        alert(`偵測到 ${data.cameras.length} 個可用相機`);
    } catch (error) {
        console.error('重新偵測相機錯誤:', error);
        alert('重新偵測相機失敗: ' + error.message);
    }
}

// 更新相機設備顯示
function updateCameraDeviceDisplay() {
    if (elements.cameraDevice) {
        elements.cameraDevice.textContent = currentCameraId !== null ? currentCameraId : 'N/A';
    }
}

// 更新相機解析度
async function updateCameraResolution(resolution) {
    try {
        const [width, height] = resolution.split('x').map(Number);
        const response = await fetch('/api/camera/resolution', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                width: width,
                height: height
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('相機解析度已更新:', result);
            
            // 重新啟動串流以套用新解析度
            if (cameraEventSource && elements.enablePreview.checked) {
                console.log('正在重新啟動串流以套用新解析度...');
                stopCameraStream();
                // 等待更長時間讓相機資源完全釋放（後端需要 1 秒）
                await new Promise(resolve => setTimeout(resolve, 1500));
                startCameraStream();
                console.log('串流已重新啟動');
            }
        } else {
            console.warn('更新相機解析度失敗');
        }
    } catch (error) {
        console.error('更新相機解析度錯誤:', error);
    }
}

// 更新預覽畫面的旋轉角度
function updatePreviewRotation(rotation) {
    // 清除之前的防抖計時器
    if (rotationUpdateTimer) {
        clearTimeout(rotationUpdateTimer);
        rotationUpdateTimer = null;
    }
    
    // 防抖處理：延遲執行以避免重複調用
    rotationUpdateTimer = setTimeout(() => {
        _updatePreviewRotationInternal(rotation);
    }, 50);
}

// 內部函數：實際執行旋轉更新
function _updatePreviewRotationInternal(rotation) {
    if (!elements.cameraPreview) {
        console.warn('updatePreviewRotation: cameraPreview 元素不存在');
        return;
    }
    
    // 如果旋轉角度沒有改變，不需要重新處理
    if (currentAppliedRotation === rotation) {
        return;
    }
    
    // 獲取預覽容器（優先使用緩存的引用，如果沒有則查找）
    let previewContainer = elements.previewContainer;
    if (!previewContainer) {
        previewContainer = elements.cameraPreview.parentElement;
        if (previewContainer) {
            elements.previewContainer = previewContainer;
        }
    }
    
    if (!previewContainer) {
        console.warn('updatePreviewRotation: 找不到預覽容器');
        return;
    }
    
    // 確認是 preview-container
    if (!previewContainer.classList.contains('preview-container')) {
        console.warn('updatePreviewRotation: 元素不是 preview-container，實際類別:', previewContainer.className);
        // 嘗試向上查找
        const parent = previewContainer.parentElement;
        if (parent && parent.classList.contains('preview-container')) {
            previewContainer = parent;
            elements.previewContainer = previewContainer;
            console.log('updatePreviewRotation: 找到正確的 preview-container');
        } else {
            return;
        }
    }
    
    console.log('updatePreviewRotation: 開始處理，rotation =', rotation);
    
    // 獲取當前容器尺寸（用於保持固定大小）
    const containerRect = previewContainer.getBoundingClientRect();
    let currentWidth = containerRect.width;
    let currentHeight = containerRect.height;
    
    // 如果尺寸異常，使用預設值
    if (currentWidth < 1 || currentHeight < 1) {
        // 使用 CSS 計算的預設尺寸
        previewContainer.style.width = '';
        previewContainer.style.height = '';
        previewContainer.style.aspectRatio = '16/9';
        void previewContainer.offsetHeight; // 強制重新計算
        const resetRect = previewContainer.getBoundingClientRect();
        currentWidth = resetRect.width;
        currentHeight = resetRect.height;
    }
    
    // 計算固定尺寸（使用當前寬度作為基準）
    const fixedWidth = currentWidth;
    
    // 根據旋轉角度調整容器寬高比，但保持固定大小
    if (rotation === 0 || rotation === 180) {
        // 0度或180度：使用 16:9 寬高比
        previewContainer.style.aspectRatio = '16/9';
        previewContainer.style.width = fixedWidth + 'px';
        previewContainer.style.height = '';
        console.log('updatePreviewRotation: 旋轉角度為', rotation + '度，容器寬高比 16:9，寬度', fixedWidth + 'px');
    } else if (rotation === 90 || rotation === 270) {
        // 90度或270度：使用 9:16 寬高比（直立式）
        // 保持寬度不變，高度會根據寬高比自動調整
        previewContainer.style.aspectRatio = '9/16';
        previewContainer.style.width = fixedWidth + 'px';
        previewContainer.style.height = '';
        console.log('updatePreviewRotation: 旋轉角度為', rotation + '度，容器寬高比 9:16（直立式），寬度', fixedWidth + 'px');
    }
    
    // 重置圖片樣式
    elements.cameraPreview.style.width = '100%';
    elements.cameraPreview.style.height = '100%';
    elements.cameraPreview.style.objectFit = 'contain';
    
    // 根據旋轉角度設定旋轉
    if (rotation === 0) {
        // 不旋轉，清除所有旋轉樣式
        elements.cameraPreview.style.transform = '';
        elements.cameraPreview.style.transformOrigin = '';
        console.log('updatePreviewRotation: 旋轉角度為 0，清除旋轉');
    } else {
        // 設定旋轉中心和旋轉角度
        elements.cameraPreview.style.transformOrigin = 'center center';
        elements.cameraPreview.style.transform = `rotate(${rotation}deg)`;
        console.log('updatePreviewRotation: 預覽畫面已旋轉', rotation + '度');
    }
    
    // 強制重新計算樣式
    void elements.cameraPreview.offsetHeight;
    void previewContainer.offsetHeight;
    
    // 記錄當前應用的旋轉角度
    currentAppliedRotation = rotation;
    
    const finalRect = previewContainer.getBoundingClientRect();
    console.log('updatePreviewRotation: 容器最終尺寸:', finalRect.width.toFixed(0) + 'x' + finalRect.height.toFixed(0));
    console.log('updatePreviewRotation: 應用的 transform =', elements.cameraPreview.style.transform || 'none');
}

// 處理重置相機
async function handleResetCamera() {
    if (isProcessing) {
        return;
    }
    
    stopCameraStream();
    
    // 等待一下再重新開始
    setTimeout(() => {
        if (elements.enablePreview.checked) {
            startCameraStream();
        }
    }, 1000);
}

// 處理清除結果
async function handleClearResults() {
    if (!confirm('確定要清除所有 OCR 結果嗎？')) {
        return;
    }
    
    try {
        const response = await fetch('/api/ocr/results/clear', {
            method: 'POST'
        });
        
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

// 顯示載入指示器
function showLoading(text = '處理中...') {
    const loadingText = elements.loadingOverlay.querySelector('.loading-text');
    if (loadingText) {
        loadingText.textContent = text;
    }
    elements.loadingOverlay.style.display = 'flex';
}

// 隱藏載入指示器
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
    stopCameraStream();
});

