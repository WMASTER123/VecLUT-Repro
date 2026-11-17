// Check the two pinned GGUF artifacts independently of the LUT implementation.
// All non-VecLUT tensor bytes; up to 36 complete rows per ternary matrix.
#include "ggml.h"
#include "gguf.h"
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <set>
#include <stdexcept>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

struct mapped_model {
    int fd=-1;size_t size=0;const uint8_t *data=nullptr;
    gguf_context *file=nullptr;ggml_context *metadata=nullptr;
    explicit mapped_model(const char *path) {
        fd=open(path,O_RDONLY);if(fd<0)throw std::runtime_error("open failed");
        struct stat info{};if(fstat(fd,&info))throw std::runtime_error("stat failed");
        size=info.st_size;
        auto *ptr=mmap(nullptr,size,PROT_READ,MAP_PRIVATE,fd,0);
        if(ptr==MAP_FAILED)throw std::runtime_error("mmap failed");
        data=static_cast<const uint8_t *>(ptr);
        file=gguf_init_from_file(path,{true,&metadata});
        if(!file)throw std::runtime_error("invalid GGUF");
    }
    ~mapped_model(){if(file)gguf_free(file);if(metadata)ggml_free(metadata);if(data)munmap(const_cast<uint8_t *>(data),size);if(fd>=0)close(fd);}
    const uint8_t *tensor(int i) const {
        size_t offset=gguf_get_data_offset(file)+gguf_get_tensor_offset(file,i);
        if(offset>size || gguf_get_tensor_size(file,i)>size-offset)throw std::runtime_error("GGUF tensor outside file");
        return data+offset;
    }
};
static int digit(int code,int k){while(k--)code/=3;return code%3-1;}
int main(int argc,char **argv)try {
    if(argc!=3)throw std::runtime_error("Usage: compare-model-packings I2_V_4.gguf I1_V_2.gguf");
    mapped_model i2(argv[1]),i1(argv[2]);
    if(gguf_get_n_tensors(i2.file)!=gguf_get_n_tensors(i1.file))throw std::runtime_error("tensor count differs");
    uint64_t compared=0,unchanged_bytes=0;int matrices=0,others=0;
    for(int i=0;i<gguf_get_n_tensors(i2.file);++i) {
        const char *name=gguf_get_tensor_name(i2.file,i);int j=gguf_find_tensor(i1.file,name);
        if(j<0)throw std::runtime_error("missing tensor");
        auto *a=ggml_get_tensor(i2.metadata,name),*b=ggml_get_tensor(i1.metadata,name);
        if(std::memcmp(a->ne,b->ne,sizeof(a->ne)))throw std::runtime_error("shape mismatch");
        const auto *p=i2.tensor(i),*q=i1.tensor(j);
        if(a->type!=GGML_TYPE_I2_V_4) {
            if(a->type!=b->type || gguf_get_tensor_size(i2.file,i)!=gguf_get_tensor_size(i1.file,j) ||
               std::memcmp(p,q,gguf_get_tensor_size(i2.file,i)))throw std::runtime_error("non-VecLUT tensor bytes differ");
            ++others;unchanged_bytes+=gguf_get_tensor_size(i2.file,i);continue;
        }
        if(b->type!=GGML_TYPE_I1_V_2 || a->ne[2]!=1 || a->ne[3]!=1)throw std::runtime_error("unexpected packing");
        int K=a->ne[0],M=a->ne[1],g5=K/20*4;std::set<int> rows={0,1,M/2,M-1};
        uint32_t state=uint32_t(i+1)*2654435761u;
        for(int r=0;r<32;++r){state=1664525u*state+1013904223u;rows.insert(state%M);}
        for(int m:rows)for(int k=0;k<K;++k) {
            int g=k/4;int v2=digit(p[(g/4)*M*4+m*4+g%4],k%4),v1;
            if(k<g5*5){int h=k/5;v1=digit(q[(h/2)*M*2+m*2+h%2],k%5);}
            else {int tail=k-g5*5;v1=digit(q[(g5+tail/4)*M+m],tail%4);}
            if(v1!=v2)throw std::runtime_error(std::string("ternary weights differ: ")+name);
            ++compared;
        }
        ++matrices;
    }
    std::cout<<"{\"passed\":true,\"matrices\":"<<matrices<<",\"compared_ternary_weights\":"<<compared
             <<",\"unchanged_tensors\":"<<others<<",\"unchanged_bytes\":"<<unchanged_bytes
             <<",\"full_ternary_scan\":false}\n";
    return matrices==182?0:1;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
