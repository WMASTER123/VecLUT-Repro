// Small, deterministic tests of the actual author packer, kernel, and ggml graph.
#include "ggml.h"
#include "ggml-cpu.h"
extern "C" {
#include "ggml-quants-vlut.h"
#include "ggml-cpu/ggml-cpu-quants-vlut.h"
}
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

#ifndef TABLE_ENTRY_SIZE
#define TABLE_ENTRY_SIZE 32
#endif
static constexpr int T = TABLE_ENTRY_SIZE;
static int failures = 0, checks = 0;
static void check(const std::string &name, bool ok, double got=0, double expected=0) {
    ++checks; failures += !ok;
    std::cout << (ok ? "PASS" : "FAIL") << '\t' << name << "\tgot=" << got
              << "\texpected=" << expected << '\n';
}
static int padded(int n) { return (n+T-1)/T*T; }

static void packing() {
    const int K=32, M=81;
    std::vector<float> w(K*M);
    for (int m=0;m<M;++m) for(int g=0;g<K/4;++g) {
        int code=(m+g)%81;
        for(int k=0;k<4;++k) { w[m*K+g*4+k]=code%3-1; code/=3; }
    }
    std::vector<uint8_t> p(K*M/4+32, 0xCD);
    size_t written=quantize_i2_v_4(w.data(),p.data(),M,K,nullptr);
    bool ok=written==size_t(K*M/4);
    for(int m=0;m<M;++m) for(int g=0;g<K/4;++g) {
        int v=p[(g/4)*M*4+m*4+g%4];
        for(int k=0;k<4;++k) { ok &= (v%3-1)==w[m*K+g*4+k]; v/=3; }
    }
    for(size_t i=written;i<p.size();++i) ok &= p[i]==0xCD;
    check("pack/all_81_patterns_two_K_tiles",ok);
    const float example[16]={-1,1,0,1};
    uint8_t pex[4]; quantize_i2_v_4(example,pex,1,16,nullptr);
    check("pack/hand_index",pex[0]==69,pex[0],69);
}

static void quantization() {
    const std::vector<std::pair<std::string,std::vector<float>>> cases={
        {"zero",{0,0,0,0}}, {"negative",{-127,-64,-1,0}},
        {"negative_dominant",{-127,1,-64,0}}, {"positive",{127,64,1,0}},
        {"tiny",{-1e-8f,5e-9f,0,1e-8f}}, {"large",{-1e20f,1e19f,0,1e20f}},
        {"subnormal",{std::numeric_limits<float>::denorm_min(),0,0,0}}
    };
    for(const auto &c:cases) {
        std::vector<int8_t> q(c.second.size()*T,42);
        float scale=0; quantize_row_i8_v_tile(c.second.data(),q.data(),c.second.size(),&scale);
        double peak=0, error=0;
        for(float x:c.second) peak=std::max(peak,std::abs(double(x)));
        bool untouched=true;
        for(size_t i=0;i<q.size();++i) if(i%T) untouched &= q[i]==42;
        for(size_t i=0;i<c.second.size();++i)
            error=std::max(error,std::abs(double(q[i*T])*scale-c.second[i]));
        // Independent error contract for symmetric per-token INT8 quantization.
        const double tolerance=peak==0 ? 0 : std::max(peak/127.0,double(std::numeric_limits<float>::min()))/2+peak*1e-6;
        check("quant/"+c.first, std::isfinite(scale) && untouched && error<=tolerance,
              error,tolerance);
        if(c.first=="negative")
            std::cout << "DETAIL\tquant/negative\tq0=" << int(q[0]) << "\tscale=" << scale << '\n';
    }
}

static void hand_example() {
    float w[16]={-1,1,0,1, 1,0,-1,0};
    uint8_t p[4]; quantize_i2_v_4(w,p,1,16,nullptr);
    std::vector<float> storage((T*16+8)/4,0);
    auto *q=reinterpret_cast<int8_t *>(storage.data());
    const int8_t a[8][2]={{2,1},{3,-2},{-1,4},{4,3},{2,-1},{0,0},{3,2},{0,0}};
    for(int k=0;k<8;++k) for(int t=0;t<2;++t) q[k*T+t]=a[k][t];
    auto *scale=reinterpret_cast<float *>(q+T*16); scale[0]=scale[1]=1;
    float out[2]={}; ggml_gemm_i2v4_i8v_lut(0,1,16,out,1,p,q,2,1);
    check("kernel/hand_two_groups_token0",out[0]==4,out[0],4);
    check("kernel/hand_two_groups_token1",out[1]==-3,out[1],-3);
}

static void direct(int K,int N,int M,int pattern) {
    std::vector<float> w(K*M);
    for(int m=0;m<M;++m) for(int k=0;k<K;++k) {
        const uint32_t value=(1664525u*uint32_t(k+1)+1013904223u*uint32_t(m+1))>>16;
        int digit=0;
        if(pattern==5) { int code=(m+(k/4)*17)%81; for(int j=0;j<k%4;++j) code/=3; digit=code%3-1; }
        w[m*K+k]=(pattern==1 || pattern==3)?1:pattern==2?-1:pattern==4?0:pattern==5?digit:int(value%3)-1;
    }
    std::vector<uint8_t> p(K*M/4); quantize_i2_v_4(w.data(),p.data(),M,K,nullptr);
    // Buffer and token layout are built independently of the production quantizer.
    std::vector<float> storage((padded(N)*K+N*4+3)/4,0);
    auto *q=reinterpret_cast<int8_t *>(storage.data());
    auto *sc=reinterpret_cast<float *>(q+padded(N)*K);
    for(int t=0;t<N;++t) {
        sc[t]=1;
        for(int k=0;k<K;++k)
            q[(t/T)*K*T+k*T+t%T]=pattern==1?127:(pattern==2 || pattern==3)?-128:((t*13+k*17)%255-127);
    }
    std::vector<float> out(N*M+16,-999);
    ggml_gemm_i2v4_i8v_lut(0,1,K,out.data(),M,p.data(),q,N,M);
    double maxerr=0, firstgot=0, firstwant=0;
    for(int t=0;t<N;++t) for(int m=0;m<M;++m) {
        int64_t want=0;
        for(int k=0;k<K;++k) want+=int(w[m*K+k])*int(q[(t/T)*K*T+k*T+t%T]);
        double err=std::abs(out[t*M+m]-double(want));
        if(err>maxerr) { maxerr=err; firstgot=out[t*M+m]; firstwant=want; }
    }
    bool guard=true; for(size_t i=N*M;i<out.size();++i) guard &= out[i]==-999;
    std::string id="kernel/K"+std::to_string(K)+"_N"+std::to_string(N)+"_M"+std::to_string(M)+"_p"+std::to_string(pattern);
    check(id,maxerr==0 && guard,firstgot,firstwant);
}

static void graph(int K,int N,int M,int threads,int slices=1) {
    ggml_init_params params={size_t(16*1024*1024),nullptr,false};
    auto *ctx=ggml_init(params);
    auto *w=ggml_new_tensor_2d(ctx,GGML_TYPE_I2_V_4,K,M);
    auto *a=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,K,N,slices);
    std::vector<float> weights(K*M);
    for(int m=0;m<M;++m) for(int k=0;k<K;++k) weights[m*K+k]=(k*7+m)%3-1;
    quantize_i2_v_4(weights.data(),w->data,M,K,nullptr);
    float *ap=static_cast<float *>(a->data);
    for(int s=0;s<slices;++s) for(int t=0;t<N;++t) for(int k=0;k<K;++k)
        ap[(s*N+t)*K+k]=k==0?127:((s*31+t*7+k*11)%101-50);
    auto *out=ggml_mul_mat(ctx,w,a);
    auto *gf=ggml_new_graph(ctx); ggml_build_forward_expand(gf,out);
    auto plan=ggml_graph_plan(gf,threads,nullptr);
    // Poison makes incorrect padding/address reuse reproducible; do not mask with zeros.
    std::vector<uint8_t> work(plan.work_size+64,0x35); plan.work_data=work.data();
    int rc=ggml_graph_compute(gf,&plan);
    const float *got=static_cast<float *>(out->data);
    double maxerr=0, firstgot=0, firstwant=0;
    std::vector<int8_t> q(K*T,0);
    for(int s=0;s<slices;++s) for(int t=0;t<N;++t) {
        float scale=0; quantize_row_i8_v_tile(ap+(s*N+t)*K,q.data(),K,&scale);
        for(int m=0;m<M;++m) {
            int64_t accum=0; for(int k=0;k<K;++k) accum+=int(weights[m*K+k])*int(q[k*T]);
            float want=float(accum)*scale;
            double err=std::abs(got[(s*N+t)*M+m]-double(want));
            if(err>maxerr) { maxerr=err; firstgot=got[(s*N+t)*M+m]; firstwant=want; }
        }
    }
    bool guard=true; for(size_t i=plan.work_size;i<work.size();++i) guard &= work[i]==0x35;
    std::string id="graph/K"+std::to_string(K)+"_N"+std::to_string(N)+"_M"+std::to_string(M)+"_t"+std::to_string(threads)+"_s"+std::to_string(slices);
    check(id,rc==0 && maxerr==0 && guard,firstgot,firstwant);
    ggml_free(ctx);
}

static void workspace() {
    auto *ctx=ggml_init({size_t(4*1024*1024),nullptr,false});
    const int K=16384,N=1;
    auto *w=ggml_new_tensor_2d(ctx,GGML_TYPE_I2_V_4,K,1);
    auto *a=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,K,N);
    auto *gf=ggml_new_graph(ctx); ggml_build_forward_expand(gf,ggml_mul_mat(ctx,w,a));
    auto plan=ggml_graph_plan(gf,1,nullptr);
    size_t required=size_t(padded(N))*K+N*sizeof(float);
    check("workspace/K16384_N1",plan.work_size>=required,plan.work_size,required);
    ggml_free(ctx);
}

int main(int argc,char **argv) {
    ggml_cpu_init();
    if(argc==3 && std::string(argv[1])=="--invalid-pack") {
        int K=std::stoi(argv[2]); std::vector<float> w(K,1); std::vector<uint8_t> p(1024,0);
        quantize_i2_v_4(w.data(),p.data(),1,K,nullptr); return 0;
    }
    if(argc==3 && std::string(argv[1])=="--invalid-kernel") {
        ggml_gemm_i2v4_i8v_lut(0,1,std::stoi(argv[2]),nullptr,1,nullptr,nullptr,1,1); return 0;
    }
    if(argc==2 && std::string(argv[1])=="--large-workspace") {
        graph(16384,1,1,1);
        return failures?1:0;
    }
    packing(); quantization(); workspace(); hand_example();
    // Deterministic counterexamples, followed by a wider regression grid.
    direct(512,1,1,1); direct(512,1,1,2);
    for(int K:{16,32,112,128,144,240,256,272,496,512,528,640,2048,2560})
        for(int N:{1,2,31,32,33,64,65}) direct(K,N,5,0);
    for(int K:{128,256,512,528,2048}) for(int p:{1,2,3}) direct(K,33,3,p);
    for(int N:{1,2,8,16,31,32,33,63,64,65}) for(int t:{1,2,4}) graph(16,N,7,t);
    for(int t:{1,2,4}) graph(528,33,7,t);
    graph(16,33,5,2,2);
    graph(16,1,5,2,2);
    direct(528,33,3,4);
    direct(32,33,81,5);
    std::cout << "SUMMARY\tchecks=" << checks << "\tfailures=" << failures << '\n';
    return failures?1:0;
}
