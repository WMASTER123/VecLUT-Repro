// Synthetic model-shaped inputs, actual fixed I2_V_4 packer/kernel/ggml graph.
#include "ggml.h"
#include "ggml-cpu.h"
extern "C" {
#include "ggml-quants-vlut.h"
#include "ggml-cpu/ggml-cpu-quants-vlut.h"
}
#include "ggml-cpu/ggml-vlut-profile.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <sched.h>
#include <vector>

using clock_type=std::chrono::steady_clock;
static double ns_since(clock_type::time_point t) {
    return std::chrono::duration<double,std::nano>(clock_type::now()-t).count();
}
struct configuration { std::string mode; int threads,iterations; std::function<void()> compute; };
int main(int argc,char **argv) try {
    if(argc!=6 && argc!=7) { std::cerr<<"Usage: bench-p2 M K N repeats target_ms [graph1|graph2|graph4|direct1]\n"; return 2; }
    int M=std::stoi(argv[1]),K=std::stoi(argv[2]),N=std::stoi(argv[3]);
    int repeats=std::stoi(argv[4]); double target_ms=std::stod(argv[5]);
    if(M<4 || K<16 || K%16 || N<1 || repeats<5 || target_ms<10) throw std::runtime_error("invalid parameters");
    const int T=TABLE_ENTRY_SIZE, padded=(N+T-1)/T*T;
    ggml_cpu_init();
    const size_t mem=size_t(16)*1024*1024+size_t(M)*K/4+size_t(K+M)*N*4;
    auto *ctx=ggml_init({mem,nullptr,false});
    auto *w=ggml_new_tensor_2d(ctx,GGML_TYPE_I2_V_4,K,M);
    auto *a=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,K,N);
    std::vector<float> weights(size_t(M)*K);
    uint32_t state=20261117;
    for(auto &v:weights) { state^=state<<13; state^=state>>17; state^=state<<5; v=int(state%3)-1; }
    quantize_i2_v_4(weights.data(),w->data,M,K,nullptr);
    auto *af=static_cast<float *>(a->data);
    for(int t=0;t<N;++t) for(int k=0;k<K;++k) af[size_t(t)*K+k]=k==0?127:(t*13+k*17)%255-127;
    auto *out=ggml_mul_mat(ctx,w,a);
    auto *gf=ggml_new_graph(ctx); ggml_build_forward_expand(gf,out);
    auto tp=ggml_threadpool_params_default(4); tp.poll=0;
    auto *pool=ggml_threadpool_new(&tp);
    std::vector<ggml_cplan> plans;
    size_t work_size=0;
    for(int t:{1,2,4}) { plans.push_back(ggml_graph_plan(gf,t,pool)); work_size=std::max(work_size,plans.back().work_size); }
    std::vector<uint8_t> workspace(work_size,0);
    for(auto &p:plans) p.work_data=workspace.data();
    std::vector<float> qstorage((size_t(padded)*K+N*4+3)/4,0);
    auto *q=reinterpret_cast<int8_t *>(qstorage.data());
    auto *sc=reinterpret_cast<float *>(q+size_t(padded)*K);
    for(int t=0;t<N;++t) quantize_row_i8_v_tile(af+size_t(t)*K,q+size_t(t/T)*K*T+t%T,K,sc+t);
    std::vector<float> direct_out(size_t(M)*N);
    auto validate=[&](const float *result) {
        for(int j=0;j<64;++j) {
            const int m=(j*131)%M, t=(j*17)%N;
            int64_t acc=0;
            for(int k=0;k<K;++k) acc+=int(weights[size_t(m)*K+k])*int(q[size_t(t/T)*K*T+k*T+t%T]);
            const float expected=float(acc)*sc[t];
            if(result[size_t(t)*M+m]!=expected) throw std::runtime_error("sampled INT64 reference mismatch");
        }
    };
    std::vector<configuration> configs;
    for(int i=0;i<3;++i) configs.push_back({"graph",plans[i].n_threads,1,[&,i] {
        if(ggml_graph_compute(gf,&plans[i])!=GGML_STATUS_SUCCESS) throw std::runtime_error("graph failed");
    }});
    configs.push_back({"direct",1,1,[&] { ggml_gemm_i2v4_i8v_lut(0,1,K,direct_out.data(),M,w->data,q,N,M); }});
    if (argc == 7) {
        const std::string selected = argv[6];
        configs.erase(std::remove_if(configs.begin(), configs.end(), [&](const configuration &c) {
            return c.mode + std::to_string(c.threads) != selected;
        }), configs.end());
        if (configs.empty()) throw std::runtime_error("unknown configuration filter");
    }
    for(auto &c:configs) {
        for(int i=0;i<3;++i) c.compute();
        validate(c.mode=="graph"?static_cast<float *>(out->data):direct_out.data());
        auto start=clock_type::now(); c.compute(); double elapsed=ns_since(start);
        c.iterations=std::clamp(int(std::ceil(target_ms*1e6/std::max(1.0,elapsed))),1,4096);
    }
    std::cout<<"mode,M,K,N,threads,repeat,iterations,wall_us,runs_s,padded_N,peak_process_kib,minor_faults,major_faults,voluntary_switches,involuntary_switches,profile,alloc_init_worker_us,build_worker_us,lookup_worker_us,widen_worker_us,output_worker_us,free_worker_us,activation_worker_us,clear_worker_us,kernel_calls_per_iteration,main_cpu_before,main_cpu_after\n";
    std::cout<<std::fixed<<std::setprecision(6);
    for(int r=0;r<repeats;++r) for(int pos=0;pos<int(configs.size());++pos) {
        auto &c=configs[(pos+r)%configs.size()];
        c.compute(); // warm after switching thread count / measurement mode
#ifdef VLUT_PROFILE
        vlut_profile_reset();
#endif
        struct rusage before{},after{}; getrusage(RUSAGE_SELF,&before);
        const int cpu_before=sched_getcpu();
        auto start=clock_type::now();
        for(int i=0;i<c.iterations;++i) c.compute();
        const double wall=ns_since(start)/c.iterations/1000;
        getrusage(RUSAGE_SELF,&after);
        uint64_t phase[9]={}; int profile=0;
#ifdef VLUT_PROFILE
        profile=1;
        for(int t=0;t<c.threads;++t) {
            const auto &v=vlut_profile_records[t];
            phase[0]+=v.alloc_init_ns; phase[1]+=v.build_ns; phase[2]+=v.lookup_ns; phase[3]+=v.widen_ns;
            phase[4]+=v.output_ns; phase[5]+=v.free_ns; phase[6]+=v.activation_ns; phase[7]+=v.clear_ns; phase[8]+=v.calls;
        }
        if(phase[8]!=uint64_t(c.iterations)*c.threads) throw std::runtime_error("unexpected kernel path/call count");
#endif
        validate(c.mode=="graph"?static_cast<float *>(out->data):direct_out.data());
        std::cout<<c.mode<<','<<M<<','<<K<<','<<N<<','<<c.threads<<','<<r<<','<<c.iterations<<','<<wall<<','<<1e6/wall<<','<<padded<<','<<after.ru_maxrss<<','
          <<after.ru_minflt-before.ru_minflt<<','<<after.ru_majflt-before.ru_majflt<<','<<after.ru_nvcsw-before.ru_nvcsw<<','<<after.ru_nivcsw-before.ru_nivcsw<<','<<profile;
        for(int j=0;j<8;++j) std::cout<<','<<double(phase[j])/c.iterations/1000;
        std::cout<<','<<double(phase[8])/c.iterations<<','<<cpu_before<<','<<sched_getcpu()<<'\n'<<std::flush;
    }
    ggml_threadpool_free(pool); ggml_free(ctx);
    return 0;
} catch(const std::exception &e) { std::cerr<<e.what()<<'\n'; return 1; }
