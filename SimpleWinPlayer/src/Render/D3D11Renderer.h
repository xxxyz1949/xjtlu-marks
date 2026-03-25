#pragma once
#include <d3d11.h>
#include <wrl/client.h>
#include <array>
#include <cstdint>
#include <windows.h>

struct ID3D11Texture2D;

struct QualityParams {
    float brightness{-0.0f};
    float contrast{1.0f};
    float saturation{1.0f};
    float sharpness{0.0f};
    float gamma{1.0f};
};

class D3D11Renderer {
public:
    D3D11Renderer();
    ~D3D11Renderer();

    bool initialize();
    void updateQuality(float brightness, float contrast, float saturation, float sharpness, float gamma);
    const QualityParams &quality() const { return m_quality; }

    ID3D11Device* device() const { return m_device.Get(); }
    ID3D11DeviceContext* context() const { return m_context.Get(); }

    bool ensureFrameTexture(int width, int height);
    bool uploadBGRA(const uint8_t* data, int stride, int width, int height);
    bool copyFromHwTexture(ID3D11Texture2D* hwTex);
    ID3D11ShaderResourceView* frameSrv() const { return m_frameSrv.Get(); }
    int frameWidth() const { return m_frameWidth; }
    int frameHeight() const { return m_frameHeight; }
    bool render();

private:
    bool createDevice();
    void createConstantBuffer();
    bool createFrameTexture(int width, int height);
    bool createSwapchainAndRTV();
    bool createPipeline();
    void updateViewport();
    bool createWindow();

    Microsoft::WRL::ComPtr<ID3D11Device> m_device;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> m_context;
    Microsoft::WRL::ComPtr<ID3D11Buffer> m_qualityCB;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> m_frameTex;
    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> m_frameSrv;
    Microsoft::WRL::ComPtr<IDXGISwapChain> m_swapchain;
    Microsoft::WRL::ComPtr<ID3D11RenderTargetView> m_rtv;
    Microsoft::WRL::ComPtr<ID3D11VertexShader> m_vs;
    Microsoft::WRL::ComPtr<ID3D11PixelShader> m_ps;
    Microsoft::WRL::ComPtr<ID3D11InputLayout> m_layout;
    Microsoft::WRL::ComPtr<ID3D11Buffer> m_vb;
    Microsoft::WRL::ComPtr<ID3D11SamplerState> m_sampler;
    D3D11_VIEWPORT m_viewport{};
    int m_frameWidth{0};
    int m_frameHeight{0};
    HWND m_hwnd{nullptr};
    QualityParams m_quality;
};
