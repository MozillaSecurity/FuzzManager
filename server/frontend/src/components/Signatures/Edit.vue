<template>
    <form v-on:submit.prevent="">
        <label for="id_shortDescription">Description</label><br/>
        <input id="id_shortDescription" class="form-control" maxlength="1023" type="text" v-model="bucket.shortDescription">
        <br/>
        <label for="id_signature">Signature</label><br/>
        <textarea id="id_signature" class="form-control" spellcheck='false' v-model="bucket.signature"></textarea>

        <div class="field">
            <input type="checkbox" id="id_frequent" v-model="bucket.frequent"/>
            <label for="id_frequent">Mark this bucket as a frequent bucket</label>
        </div>

        <div class="field">
            <input type="checkbox" id="id_permanent" v-model="bucket.permanent"/>
            <label for="id_permanent">Mark this bucket as a permanent bucket</label>
        </div>

        <div class="field">
            <input type="checkbox" id="id_reassign" v-model="reassign"/>
            <label for="id_reassign">Reassign matching crashes (unassigned crashes and crashes assigned to this bucket will be reassigned)</label>
        </div>
        <div class="btn-group">
            <button type="submit" class="btn btn-success" v-on:click="update(true)">Save</button>
            <button type="submit" class="btn btn-default" v-on:click="update(false)">Preview</button>
        </div>
    </form>
</template>

<script>
import * as api from '../../api'

export default {
    props: {
        bucketId: Number,
    },
    data: () => ({
        bucket: {},
        reassign: true,
    }),
    async mounted () {
        this.bucket = await api.retrieveBucket(this.bucketId)
    },
    methods: {
        async update (save) {
            console.log("Save: " + save)
            console.log("Update called")
            const payload = {
                signature: this.bucket.signature,
                shortDescription: this.bucket.shortDescription,
                frequent: this.bucket.frequent,
                permanent: this.bucket.permanent,
            }
            try {
                bucket = await api.updateBucket({
                    id: this.bucketId,
                    params: {save: save, reassign: this.reassign},
                    ...payload
                })
            } catch (err) {
                console.log(err)
            }
        }
    }
}
</script>

<style scoped>
</style>