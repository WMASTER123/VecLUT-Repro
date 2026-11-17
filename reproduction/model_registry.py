"""Pinned GGUF artifacts. Only these files are downloaded, never full repositories."""
MODELS = {
    'falcon3-1b-i2v4': dict(
        repo='XXXXyu/Falcon3-1B-Instruct-1.58bit-vlut-gguf',
        revision='1cf5c2dc924ab7117053758da68f8376da95fc4d',
        file='ggml-model-I2_V_4.gguf', size_bytes=659366272,
        sha256='6eb67473189b8b6d1a02cdc723b2f284b0e247eba27619c46117fd2d592c6b94',
        tensor_type='i2_v_4', tensor_count=126),
    'bitnet-3b-i2v4': dict(
        repo='XXXXyu/bitnet_b1_58-3B-vlut-gguf',
        revision='9758ca86f6411ea903399e45537d6fa651243524',
        file='ggml-model-I2_V_4.gguf', size_bytes=916849184,
        sha256='8f9dd970b58c70180bffcf6bdbe0666b083913675d457a50decbf3cef8ec3d7e',
        tensor_type='i2_v_4', tensor_count=182),
    'bitnet-3b-i1v2': dict(
        repo='XXXXyu/bitnet_b1_58-3B-vlut-gguf',
        revision='9758ca86f6411ea903399e45537d6fa651243524',
        file='ggml-model-I1_V_2.gguf', size_bytes=755773984,
        sha256='be9983b8bdd554deca39c0bf93a58e746cdce2a4611fa1ba3ea1aeffe08f2e7f',
        tensor_type='i1_v_2', tensor_count=182),
}
