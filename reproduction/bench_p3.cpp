// Thin measurement harness around the author's actual llama/ggml implementation.
#include "llama.h"
#include "gguf.h"
#include "ggml-cpu/ggml-vlut-profile.h"
#include "json.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <vector>

using json=nlohmann::ordered_json;
using Clock=std::chrono::steady_clock;
static double ms(Clock::time_point start) {return std::chrono::duration<double,std::milli>(Clock::now()-start).count();}
static void emit(const json &v) {std::cout<<v.dump(-1,' ',false,json::error_handler_t::replace)<<'\n'<<std::flush;}
static void reset_trace() {
#ifdef VLUT_PROFILE
    vlut_profile_reset();
#endif
}
static uint64_t calls() {
    uint64_t n=0;
#ifdef VLUT_PROFILE
    for(const auto &r:vlut_profile_records) n+=r.calls;
#endif
    return n;
}
static bool tracing() {
#ifdef VLUT_PROFILE
    return true;
#else
    return false;
#endif
}
static void checked_decode(llama_context *ctx,llama_batch batch) {
    int rc=llama_decode(ctx,batch);
    if(rc) throw std::runtime_error("llama_decode returned "+std::to_string(rc));
    llama_synchronize(ctx);
}
static llama_token greedy(llama_context *ctx,int row,int n_vocab) {
    const float *logits=llama_get_logits_ith(ctx,row);
    if(!logits) throw std::runtime_error("missing logits");
    int best=0;
    for(int i=0;i<n_vocab;++i) {
        if(!std::isfinite(logits[i])) throw std::runtime_error("non-finite logits");
        if(logits[i]>logits[best]) best=i;
    }
    return best;
}
static std::vector<llama_token> tokenize(const llama_vocab *vocab,const std::string &text) {
    int n=-llama_tokenize(vocab,text.data(),text.size(),nullptr,0,true,true);
    if(n<=0) throw std::runtime_error("empty tokenization");
    std::vector<llama_token> t(n);
    int got=llama_tokenize(vocab,text.data(),text.size(),t.data(),n,true,true);
    if(got!=n) throw std::runtime_error("tokenization mismatch");
    return t;
}
static std::string piece(const llama_vocab *vocab,llama_token t) {
    std::vector<char> b(128); int n=llama_token_to_piece(vocab,t,b.data(),b.size(),0,true);
    if(n<0) {b.resize(-n);n=llama_token_to_piece(vocab,t,b.data(),b.size(),0,true);}
    if(n<0) throw std::runtime_error("token detokenization failed");
    return {b.data(),size_t(n)};
}

int main(int argc,char **argv) try {
    if(argc!=8) throw std::runtime_error("Usage: bench-p3 model.gguf mode(prefill|decode|smoke) P G B threads repeats");
    std::string path=argv[1],mode=argv[2];
    int P=std::stoi(argv[3]),G=std::stoi(argv[4]),B=std::stoi(argv[5]),threads=std::stoi(argv[6]),repeats=std::stoi(argv[7]);
    if((mode!="prefill"&&mode!="decode"&&mode!="smoke")||P<1||G<0||B<1||B>16||threads<1||threads>4||repeats<1||P>512||G>128)
        throw std::runtime_error("invalid parameters");
    ggml_context *metadata=nullptr;
    auto *gguf=gguf_init_from_file(path.c_str(),{true,&metadata});
    if(!gguf) throw std::runtime_error("cannot inspect GGUF");
    std::map<std::string,int> types;
    for(int i=0;i<gguf_get_n_tensors(gguf);++i) types[ggml_type_name(gguf_get_tensor_type(gguf,i))]++;
    json matrices=json::array();
    for(auto *tensor=ggml_get_first_tensor(metadata);tensor;tensor=ggml_get_next_tensor(metadata,tensor)) {
        if(tensor->type==GGML_TYPE_I2_V_4 || tensor->type==GGML_TYPE_I1_V_2)
            matrices.push_back({{"name",tensor->name},{"type",ggml_type_name(tensor->type)},
                                {"K",tensor->ne[0]},{"M",tensor->ne[1]}});
    }
    if(!types.count(ggml_type_name(GGML_TYPE_I2_V_4))) throw std::runtime_error("GGUF has no I2_V_4 tensor");
    gguf_free(gguf);ggml_free(metadata);
    llama_backend_init();
    auto mp=llama_model_default_params();mp.n_gpu_layers=0;mp.use_mmap=true;
    auto start=Clock::now();auto *model=llama_model_load_from_file(path.c_str(),mp);double load_ms=ms(start);
    if(!model) throw std::runtime_error("model load failed");
    auto *vocab=llama_model_get_vocab(model);int n_vocab=llama_vocab_n_tokens(vocab);
    std::string prompt;
    std::vector<llama_token> input;
    if(mode=="smoke") {
        const char *question="What is the capital of France? Answer in one short sentence.";
        const char *tmpl=llama_model_chat_template(model);
        if(tmpl) {
            llama_chat_message msg{"user",question};
            std::vector<char> buf(8192);
            int n=llama_chat_apply_template(tmpl,&msg,1,true,buf.data(),buf.size());
            if(n<0||n>int(buf.size())) throw std::runtime_error("unsupported model chat template");
            prompt.assign(buf.data(),n);
        } else {
            // The BitNet checkpoint is a base model, not an instruction-tuned assistant.
            prompt="Paris is the capital of France. The city is known for";
        }
        input=tokenize(vocab,prompt);P=input.size();
    } else {
        while(true) {
            prompt+=" The small research team studies efficient language models on a local CPU. Clear experiments use a fixed input and record their results.";
            input=tokenize(vocab,prompt);
            if(int(input.size())>=P) break;
        }
        input.resize(P);
    }
    auto cp=llama_context_default_params();
    cp.n_ctx=std::max(512,(P+G+8)*B);cp.n_batch=512;cp.n_ubatch=512;cp.n_seq_max=B;
    cp.n_threads=threads;cp.n_threads_batch=threads;cp.offload_kqv=false;cp.flash_attn=false;cp.no_perf=false;
    start=Clock::now();auto *ctx=llama_init_from_model(model,cp);double context_ms=ms(start);
    if(!ctx) throw std::runtime_error("context initialization failed");
    auto batch=llama_batch_init(std::max(P,B),0,B);
    emit({{"record","setup"},{"mode",mode},{"P",P},{"G",G},{"B",B},{"threads",threads},{"repeats",repeats},
          {"profile",tracing()},{"tensor_types",types},{"vlut_matrices",matrices},{"load_ms",load_ms},{"context_ms",context_ms},{"n_ctx",llama_n_ctx(ctx)},
          {"n_vocab",n_vocab},{"input_tokens",input},{"input_text",prompt},{"shared_prompt",B>1}});
    for(int rep=-1;rep<repeats;++rep) {
        llama_kv_cache_clear(ctx);
        struct rusage before{};getrusage(RUSAGE_SELF,&before);
        batch.n_tokens=P;
        for(int i=0;i<P;++i) {
            batch.token[i]=input[i];batch.pos[i]=i;batch.n_seq_id[i]=B;batch.logits[i]=(i==P-1);
            for(int s=0;s<B;++s) batch.seq_id[i][s]=s;
        }
        reset_trace(); start=Clock::now();checked_decode(ctx,batch);double prefill_ms=ms(start);uint64_t pcalls=calls();
        llama_token first=greedy(ctx,P-1,n_vocab);
        std::vector<llama_token> next(B,first);std::vector<std::vector<llama_token>> generated(B);
        double model_decode_ms=0,loop_ms=0;int steps=0;uint64_t dcalls=0;
        if(mode!="prefill") {
            reset_trace();auto loop_start=Clock::now();
            for(int step=0;step<G;++step) {
                if(mode=="smoke"&&llama_vocab_is_eog(vocab,next[0])) break;
                batch.n_tokens=B;
                for(int s=0;s<B;++s) {
                    generated[s].push_back(next[s]);batch.token[s]=next[s];batch.pos[s]=P+step;
                    batch.n_seq_id[s]=1;batch.seq_id[s][0]=s;batch.logits[s]=true;
                }
                start=Clock::now();checked_decode(ctx,batch);model_decode_ms+=ms(start);++steps;
                for(int s=0;s<B;++s) next[s]=greedy(ctx,s,n_vocab);
            }
            loop_ms=ms(loop_start);dcalls=calls();
        }
        if(tracing()&&(pcalls==0||(steps>0&&dcalls==0))) throw std::runtime_error("I2_V_4 kernel path not observed");
        std::vector<std::string> text(B);
        for(int s=0;s<B;++s) for(auto token:generated[s]) text[s]+=piece(vocab,token);
        struct rusage usage{};getrusage(RUSAGE_SELF,&usage);
        emit({{"record",rep<0?"warmup":"sample"},{"repeat",rep},{"prefill_ms",prefill_ms},{"decode_model_ms",model_decode_ms},
              {"decode_loop_ms",loop_ms},{"decode_steps",steps},{"decoded_tokens",steps*B},{"prefill_tps",P*1000/prefill_ms},
              {"decode_total_tps",steps?steps*B*1000/loop_ms:0},{"decode_per_sequence_tps",steps?steps*1000/loop_ms:0},
              {"prefill_i2v4_worker_calls",pcalls},{"decode_i2v4_worker_calls",dcalls},{"peak_process_kib",usage.ru_maxrss},
              {"major_faults",usage.ru_majflt-before.ru_majflt},{"minor_faults",usage.ru_minflt-before.ru_minflt},
              {"involuntary_switches",usage.ru_nivcsw-before.ru_nivcsw},
              {"output_token_ids",generated},{"output_text",text},{"finite_logits",true}});
    }
    llama_batch_free(batch);llama_free(ctx);llama_model_free(model);llama_backend_free();return 0;
} catch(const std::exception &e) {std::cerr<<"P3 failure: "<<e.what()<<'\n';return 1;}
