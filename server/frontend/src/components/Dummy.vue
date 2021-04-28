<template>
    <div>
        <h1 hidden>Hello, I'm a Dummy component.</h1>
    </div>
</template>

<script>
export default {
    mounted () {
        console.log("----------------------------------------")
        console.log("Dummy Vue component was properly loaded.")
        console.log("----------------------------------------")
    }
}
</script>

<style scoped>
</style>