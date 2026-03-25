#include "D3D11Renderer.h"
#include <stdexcept>
#include <cstring>
#include <d3dcompiler.h>
#include <dxgi.h>

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
    createWindow();
    createSwapchainAndRTV();
    createPipeline();
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

bool D3D11Renderer::createWindow() {
    if (m_hwnd) return true;
    const wchar_t *clsName = L"SimpleWinPlayerD3D11Window";
    static bool registered = false;
    if (!registered) {
        WNDCLASSEXW wc{ sizeof(WNDCLASSEXW) };
        wc.lpfnWndProc = DefWindowProcW;
        wc.hInstance = GetModuleHandleW(nullptr);
        wc.lpszClassName = clsName;
        RegisterClassExW(&wc);
        registered = true;
    }
    m_hwnd = CreateWindowExW(0, clsName, L"SimpleWinPlayer Video",
                             WS_OVERLAPPEDWINDOW | WS_VISIBLE,
                             CW_USEDEFAULT, CW_USEDEFAULT, 1280, 720,
                             nullptr, nullptr, GetModuleHandleW(nullptr), nullptr);
    return m_hwnd != nullptr;
}

bool D3D11Renderer::createSwapchainAndRTV() {
    if (!m_device || !m_context || !m_hwnd) return false;

    ComPtr<IDXGIDevice> dxgiDevice;
    if (FAILED(m_device.As(&dxgiDevice))) return false;
    ComPtr<IDXGIAdapter> adapter;
    if (FAILED(dxgiDevice->GetAdapter(&adapter))) return false;
    ComPtr<IDXGIFactory> factory;
    if (FAILED(adapter->GetParent(__uuidof(IDXGIFactory), reinterpret_cast<void**>(factory.GetAddressOf())))) return false;

    DXGI_SWAP_CHAIN_DESC desc{};
    desc.BufferCount = 2;
    desc.BufferDesc.Width = 1280;
    desc.BufferDesc.Height = 720;
    desc.BufferDesc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    desc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    desc.OutputWindow = m_hwnd;
    desc.SampleDesc.Count = 1;
    desc.Windowed = TRUE;
    desc.SwapEffect = DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL;

    if (FAILED(factory->CreateSwapChain(m_device.Get(), &desc, m_swapchain.ReleaseAndGetAddressOf()))) {
        return false;
    }

    ComPtr<ID3D11Texture2D> backbuffer;
    if (FAILED(m_swapchain->GetBuffer(0, __uuidof(ID3D11Texture2D), reinterpret_cast<void**>(backbuffer.GetAddressOf())))) {
        return false;
    }
    if (FAILED(m_device->CreateRenderTargetView(backbuffer.Get(), nullptr, m_rtv.GetAddressOf()))) {
        return false;
    }

    updateViewport();
    return true;
}

void D3D11Renderer::updateViewport() {
    if (!m_rtv) return;
    D3D11_TEXTURE2D_DESC desc{};
    ComPtr<ID3D11Texture2D> tex;
    m_rtv->GetResource(reinterpret_cast<ID3D11Resource**>(tex.GetAddressOf()));
    tex->GetDesc(&desc);
    m_viewport.TopLeftX = 0;
    m_viewport.TopLeftY = 0;
    m_viewport.Width = static_cast<float>(desc.Width);
    m_viewport.Height = static_cast<float>(desc.Height);
    m_viewport.MinDepth = 0.0f;
    m_viewport.MaxDepth = 1.0f;
}

bool D3D11Renderer::createPipeline() {
    if (!m_device) return false;

    // Simple fullscreen quad
    struct Vertex { float pos[2]; float uv[2]; };
    const Vertex verts[] = {
        {{-1.f, -1.f}, {0.f, 1.f}},
        {{-1.f,  1.f}, {0.f, 0.f}},
        {{ 1.f, -1.f}, {1.f, 1.f}},
        {{ 1.f,  1.f}, {1.f, 0.f}},
    };
    D3D11_BUFFER_DESC vbDesc{};
    vbDesc.ByteWidth = sizeof(verts);
    vbDesc.Usage = D3D11_USAGE_IMMUTABLE;
    vbDesc.BindFlags = D3D11_BIND_VERTEX_BUFFER;
    D3D11_SUBRESOURCE_DATA vbData{};
    vbData.pSysMem = verts;
    if (FAILED(m_device->CreateBuffer(&vbDesc, &vbData, m_vb.GetAddressOf()))) return false;

    static const char* vsSrc = R"(
        struct VSInput { float2 pos : POSITION; float2 uv : TEXCOORD0; };
        struct PSInput { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; };
        PSInput main(VSInput input) {
            PSInput o;
            o.pos = float4(input.pos, 0, 1);
            o.uv = input.uv;
            return o;
        }
    )";

    static const char* psSrc = R"(
        Texture2D tex0 : register(t0);
        SamplerState samp0 : register(s0);
        struct PSInput { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; };
        float4 main(PSInput input) : SV_Target {
            return tex0.Sample(samp0, input.uv);
        }
    )";

    ComPtr<ID3DBlob> vsBlob, psBlob, errBlob;
    if (FAILED(D3DCompile(vsSrc, strlen(vsSrc), nullptr, nullptr, nullptr, "main", "vs_5_0", 0, 0, vsBlob.GetAddressOf(), errBlob.GetAddressOf()))) {
        return false;
    }
    if (FAILED(D3DCompile(psSrc, strlen(psSrc), nullptr, nullptr, nullptr, "main", "ps_5_0", 0, 0, psBlob.GetAddressOf(), errBlob.ReleaseAndGetAddressOf()))) {
        return false;
    }

    if (FAILED(m_device->CreateVertexShader(vsBlob->GetBufferPointer(), vsBlob->GetBufferSize(), nullptr, m_vs.GetAddressOf()))) return false;
    if (FAILED(m_device->CreatePixelShader(psBlob->GetBufferPointer(), psBlob->GetBufferSize(), nullptr, m_ps.GetAddressOf()))) return false;

    D3D11_INPUT_ELEMENT_DESC layoutDesc[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, sizeof(float)*2, D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    if (FAILED(m_device->CreateInputLayout(layoutDesc, 2, vsBlob->GetBufferPointer(), vsBlob->GetBufferSize(), m_layout.GetAddressOf()))) return false;

    D3D11_SAMPLER_DESC samp{};
    samp.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    samp.AddressU = samp.AddressV = samp.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    samp.MaxLOD = D3D11_FLOAT32_MAX;
    if (FAILED(m_device->CreateSamplerState(&samp, m_sampler.GetAddressOf()))) return false;

    return true;
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

bool D3D11Renderer::render() {
    if (!m_swapchain || !m_rtv || !m_frameSrv) return false;

    float clear[4] = {0, 0, 0, 1};
    m_context->ClearRenderTargetView(m_rtv.Get(), clear);
    m_context->OMSetRenderTargets(1, m_rtv.GetAddressOf(), nullptr);
    m_context->RSSetViewports(1, &m_viewport);

    UINT stride = sizeof(float) * 4;
    UINT offset = 0;
    m_context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);
    m_context->IASetVertexBuffers(0, 1, m_vb.GetAddressOf(), &stride, &offset);
    m_context->IASetInputLayout(m_layout.Get());
    m_context->VSSetShader(m_vs.Get(), nullptr, 0);
    m_context->PSSetShader(m_ps.Get(), nullptr, 0);
    m_context->PSSetShaderResources(0, 1, m_frameSrv.GetAddressOf());
    m_context->PSSetSamplers(0, 1, m_sampler.GetAddressOf());
    m_context->Draw(4, 0);
    m_swapchain->Present(1, 0);
    return true;
}
