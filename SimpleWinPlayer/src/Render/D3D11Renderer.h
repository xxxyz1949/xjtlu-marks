#pragma once
#include <d3d11.h>
#include <wrl/client.h>
#include <array>
#include <cstdint>

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

private:
    bool createDevice();
    void createConstantBuffer();
    bool createFrameTexture(int width, int height);

    Microsoft::WRL::ComPtr<ID3D11Device> m_device;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> m_context;
    Microsoft::WRL::ComPtr<ID3D11Buffer> m_qualityCB;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> m_frameTex;
    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> m_frameSrv;
    int m_frameWidth{0};
    int m_frameHeight{0};
    QualityParams m_quality;
};
