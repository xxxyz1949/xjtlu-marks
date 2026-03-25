#include "D3D11Renderer.h"
#include <stdexcept>
#include <cstring>

using Microsoft::WRL::ComPtr;

D3D11Renderer::D3D11Renderer() {
    initialize();
}

D3D11Renderer::~D3D11Renderer() {
}

bool D3D11Renderer::initialize() {
    if (!createDevice()) {
        return false;
    }
    createConstantBuffer();
    return true;
}

bool D3D11Renderer::createDevice() {
    UINT flags = D3D11_CREATE_DEVICE_BGRA_SUPPORT;
#ifdef _DEBUG
    flags |= D3D11_CREATE_DEVICE_DEBUG;
#endif
    D3D_FEATURE_LEVEL fl;
    static const D3D_FEATURE_LEVEL levels[] = {
        D3D_FEATURE_LEVEL_11_1,
        D3D_FEATURE_LEVEL_11_0,
    };
    HRESULT hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, flags,
                                   levels, ARRAYSIZE(levels), D3D11_SDK_VERSION,
                                   m_device.GetAddressOf(), &fl, m_context.GetAddressOf());
    return SUCCEEDED(hr);
}

void D3D11Renderer::createConstantBuffer() {
    if (!m_device) return;
    D3D11_BUFFER_DESC desc = {};
    desc.ByteWidth = sizeof(QualityParams);
    desc.Usage = D3D11_USAGE_DYNAMIC;
    desc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
    m_device->CreateBuffer(&desc, nullptr, m_qualityCB.GetAddressOf());
}

void D3D11Renderer::updateQuality(float brightness, float contrast, float saturation, float sharpness, float gamma) {
    m_quality.brightness = brightness;
    m_quality.contrast = contrast;
    m_quality.saturation = saturation;
    m_quality.sharpness = sharpness;
    m_quality.gamma = gamma;

    if (!m_context || !m_qualityCB) return;
    D3D11_MAPPED_SUBRESOURCE mapped{};
    if (SUCCEEDED(m_context->Map(m_qualityCB.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &mapped))) {
        memcpy(mapped.pData, &m_quality, sizeof(QualityParams));
        m_context->Unmap(m_qualityCB.Get(), 0);
    }
}

bool D3D11Renderer::createFrameTexture(int width, int height) {
    m_frameTex.Reset();
    m_frameSrv.Reset();

    D3D11_TEXTURE2D_DESC desc{};
    desc.Width = width;
    desc.Height = height;
    desc.MipLevels = 1;
    desc.ArraySize = 1;
    desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    desc.SampleDesc.Count = 1;
    desc.Usage = D3D11_USAGE_DEFAULT;
    desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;

    HRESULT hr = m_device->CreateTexture2D(&desc, nullptr, m_frameTex.GetAddressOf());
    if (FAILED(hr)) {
        return false;
    }

    hr = m_device->CreateShaderResourceView(m_frameTex.Get(), nullptr, m_frameSrv.GetAddressOf());
    if (FAILED(hr)) {
        m_frameTex.Reset();
        return false;
    }

    m_frameWidth = width;
    m_frameHeight = height;
    return true;
}

bool D3D11Renderer::ensureFrameTexture(int width, int height) {
    if (!m_device) return false;
    if (m_frameTex && width == m_frameWidth && height == m_frameHeight) return true;
    return createFrameTexture(width, height);
}

bool D3D11Renderer::uploadBGRA(const uint8_t* data, int stride, int width, int height) {
    if (!ensureFrameTexture(width, height)) return false;
    D3D11_BOX box{0, 0, 0, static_cast<UINT>(width), static_cast<UINT>(height), 1};
    m_context->UpdateSubresource(m_frameTex.Get(), 0, &box, data, stride, 0);
    return true;
}

bool D3D11Renderer::copyFromHwTexture(ID3D11Texture2D* hwTex) {
    if (!hwTex) return false;
    D3D11_TEXTURE2D_DESC desc{};
    hwTex->GetDesc(&desc);
    if (!ensureFrameTexture(static_cast<int>(desc.Width), static_cast<int>(desc.Height))) {
        return false;
    }
    m_context->CopyResource(m_frameTex.Get(), hwTex);
    return true;
}
