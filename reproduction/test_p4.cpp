// I1_V_2: independent base-3 decoding and INT64 oracle against production code.
#include "ggml.h"
#include "ggml-cpu.h"
extern "C" {
#include "ggml-quants-vlut.h"
#include "ggml-cpu/ggml-cpu-quants-vlut.h"
}
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

#ifndef TABLE_ENTRY_SIZE
#define TABLE_ENTRY_SIZE 32
#endif
static constexpr int T=TABLE_ENTRY_SIZE;
static int checks=0,failures=0;
static void check(const std::string &name,bool ok,double got=0,double want=0) {
    ++checks;failures+=!ok;
    std::cout<<(ok?"PASS":"FAIL")<<'\t'<<name<<"\tgot="<<got<<"\texpected="<<want<<'\n';
}
static int padded(int n) {return (n+T-1)/T*T;}
static int packed_row(int k) {return (k/20)*4+(k%20)/4;}
static int trit(int code,int digit) {while(digit--)code/=3;return code%3-1;}

static void packing(int K) {
    const int M=243,g5=K/20*4,g4=K%20/4;
    std::vector<float> w(K*M);
    for(int m=0;m<M;++m) {
        for(int g=0;g<g5;++g)for(int k=0;k<5;++k)w[m*K+g*5+k]=trit((m+g)%243,k);
        for(int g=0;g<g4;++g)for(int k=0;k<4;++k)w[m*K+g5*5+g*4+k]=trit((m+g)%81,k);
    }
    std::vector<uint8_t> p(packed_row(K)*M+32,0xCD);
    size_t written=quantize_i1_v_2(w.data(),p.data(),M,K,nullptr);
    bool ok=written==size_t(packed_row(K)*M);
    for(int m=0;m<M;++m) {
        for(int g=0;g<g5;++g)for(int k=0;k<5;++k)
            ok&=trit(p[(g/2)*M*2+m*2+g%2],k)==w[m*K+g*5+k];
        for(int g=0;g<g4;++g)for(int k=0;k<4;++k)
            ok&=trit(p[(g5+g)*M+m],k)==w[m*K+g5*5+g*4+k];
    }
    for(size_t i=written;i<p.size();++i)ok&=p[i]==0xCD;
    check("pack/K"+std::to_string(K)+"_all243_and81",ok);
}

static void direct(int K,int N,int M,int pattern) {
    std::vector<float> w(K*M);
    for(int m=0;m<M;++m)for(int k=0;k<K;++k)
        w[m*K+k]=pattern==1||pattern==3?1:pattern==2?-1:pattern==4?0:trit((m+k/5)%243,k%5);
    std::vector<uint8_t> p(packed_row(K)*M);
    quantize_i1_v_2(w.data(),p.data(),M,K,nullptr);
    std::vector<float> storage((padded(N)*K+N*4+3)/4,0);
    auto *q=reinterpret_cast<int8_t *>(storage.data());
    auto *sc=reinterpret_cast<float *>(q+padded(N)*K);
    for(int t=0;t<N;++t) {
        sc[t]=1;
        for(int k=0;k<K;++k)q[(t/T)*K*T+k*T+t%T]=pattern==1?127:pattern==2||pattern==3?-128:(t*13+k*17)%255-127;
    }
    std::vector<float> out(N*M+16,-999);
    ggml_gemm_i1v2_i8v_lut(0,1,K,out.data(),M,p.data(),q,N,M);
    double error=0,got=0,want=0;
    for(int t=0;t<N;++t)for(int m=0;m<M;++m) {
        int64_t ref=0;
        for(int k=0;k<K;++k)ref+=int(w[m*K+k])*int(q[(t/T)*K*T+k*T+t%T]);
        if(std::abs(out[t*M+m]-double(ref))>error){error=std::abs(out[t*M+m]-double(ref));got=out[t*M+m];want=ref;}
    }
    bool guard=std::all_of(out.begin()+N*M,out.end(),[](float v){return v==-999;});
    check("kernel/K"+std::to_string(K)+"_N"+std::to_string(N)+"_M"+std::to_string(M)+"_p"+std::to_string(pattern),error==0&&guard,got,want);
}

static void graph(int K,int N,int M,int threads,int slices=1) {
    auto *ctx=ggml_init({size_t(16*1024*1024),nullptr,false});
    auto *w=ggml_new_tensor_2d(ctx,GGML_TYPE_I1_V_2,K,M);
    auto *a=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,K,N,slices);
    std::vector<float> weights(K*M);
    for(int m=0;m<M;++m)for(int k=0;k<K;++k)weights[m*K+k]=((k*17+m*31+k/5)%3)-1;
    quantize_i1_v_2(weights.data(),w->data,M,K,nullptr);
    auto *ap=static_cast<float *>(a->data);
    for(int s=0;s<slices;++s)for(int t=0;t<N;++t)for(int k=0;k<K;++k)
        ap[(s*N+t)*K+k]=k==0?-127:((s*31+t*7+k*11)%101-50);
    auto *out=ggml_mul_mat(ctx,w,a);auto *gf=ggml_new_graph(ctx);ggml_build_forward_expand(gf,out);
    auto plan=ggml_graph_plan(gf,threads,nullptr);
    std::vector<uint8_t> work(plan.work_size+64,0x35);plan.work_data=work.data();
    int rc=ggml_graph_compute(gf,&plan);const auto *got=static_cast<float *>(out->data);
    std::vector<int8_t> q(K*T,0);double error=0,firstgot=0,firstwant=0;
    for(int s=0;s<slices;++s)for(int t=0;t<N;++t) {
        float scale=0;quantize_row_i8_v_tile(ap+(s*N+t)*K,q.data(),K,&scale);
        for(int m=0;m<M;++m) {
            int64_t sum=0;for(int k=0;k<K;++k)sum+=int(weights[m*K+k])*int(q[k*T]);
            float want=float(sum)*scale;double e=std::abs(got[(s*N+t)*M+m]-double(want));
            if(e>error){error=e;firstgot=got[(s*N+t)*M+m];firstwant=want;}
        }
    }
    bool guard=std::all_of(work.begin()+plan.work_size,work.end(),[](uint8_t v){return v==0x35;});
    check("graph/K"+std::to_string(K)+"_N"+std::to_string(N)+"_M"+std::to_string(M)+"_t"+std::to_string(threads)+"_s"+std::to_string(slices),rc==0&&error==0&&guard,firstgot,firstwant);
    ggml_free(ctx);
}

int main(int argc,char **argv) {
    ggml_cpu_init();
    if(argc==2 && std::string(argv[1])=="--small-graph") {graph(4,33,7,4);return failures?1:0;}
    if(argc==3 && std::string(argv[1])=="--invalid-pack") {
        int K=std::stoi(argv[2]);std::vector<float>w(std::max(1,K),1);std::vector<uint8_t>p(64);
        quantize_i1_v_2(w.data(),p.data(),1,K,nullptr);return 0;
    }
    if(argc==3 && std::string(argv[1])=="--invalid-kernel") {
        ggml_gemm_i1v2_i8v_lut(0,1,std::stoi(argv[2]),nullptr,1,nullptr,nullptr,1,1);return 0;
    }
    // Packing and table coverage, group boundary, signed extremes, token tails.
    for(int K:{4,8,12,16,20,24,28,32,36,40,56,160,640,644})packing(K);
    for(int K:{4,16,24,36,164}) {
        auto *ctx=ggml_init({1024*1024,nullptr,false});
        auto *w=ggml_new_tensor_2d(ctx,GGML_TYPE_I1_V_2,K,7);
        check("layout/K"+std::to_string(K),w->nb[1]==size_t(packed_row(K)) && ggml_is_contiguous(w),w->nb[1],packed_row(K));
        ggml_free(ctx);
    }
    for(int K:{4,16,20,24,36,40,156,160,164,240,256,636,640,644,1284,3200,8640})
        for(int N:{1,31,32,33,65})direct(K,N,5,0);
    direct(40,33,243,0);
    for(int K:{160,240,256,640,644,3200,8640})for(int p:{1,2,3,4})direct(K,33,3,p);
    for(int K:{16,20,24,36,160,164,640,644,3200,8640})
        for(int t:{1,2,4})for(int N:{1,32,33})graph(K,N,7,t);
    graph(36,65,5,4,2);graph(3200,33,5,4,2);
    std::cout<<"SUMMARY\tchecks="<<checks<<"\tfailures="<<failures<<'\n';return failures?1:0;
}
