<template>
<table class="table table-condensed table-hover table-bordered table-db">
    <thead>
        <tr>
            <th style="width: 25px;">ID</th>
            <th style="width: 50px;">Date Added</th>
            <th style="width: 100px;">Short Signature</th>
            <th style="width: 40px;">Crash Address</th>
            <th style="width: 50px;">Test Status</th>
            <th style="width: 50px;">Product</th>
            <th style="width: 50px;">Version</th>
            <th style="width: 25px;">Platform</th>
            <th style="width: 25px;">OS</th>
            <th style="width: 40px;">Tool</th>
        </tr>
    </thead>
    <tbody>
        <tr v-for="(entry, index) in entries" :key="entry.pk" :class="{'odd': index % 2 === 0, 'even': index % 2 !== 0}">
            <td>
                <a :href="entry.url">{{ entry.pk }}</a>
            </td>
            <!-- TODO: Restore date formatting (previously: `entry.created|date:"r"`) -->
            <td>{{ entry.created }}</td>
            <td>{{ entry.shortSignature }}</td>
            <td>{{ entry.crashAddress }}</td>
            <td>{{ testCaseText(entry) }}</td>
            <td>{{ entry.product.name }}</td>
            <td>{{ entry.product.version }}</td>
            <td>{{ entry.platform.name }}</td>
            <td>
                <img width="16px" height="16px" alt="Linux" :src="staticLogo(entry.os.name)" v-if="entry.os.name == 'linux'"/>
                <img width="16px" height="16px" alt="MacOS" :src="staticLogo(entry.os.name)" v-else-if="entry.os.name == 'macosx'"/>
                <img width="16px" height="16px" alt="Windows" :src="staticLogo(entry.os.name)" v-else-if="entry.os.name == 'windows'"/>
                <img width="16px" height="16px" alt="Android" :src="staticLogo(entry.os.name)" v-else-if="entry.os.name == 'android'"/>
                <template v-else>{{ entry.os.name }}</template>
            </td>
            <td>{{ entry.tool.name }}</td>
        </tr>
    </tbody>
</table>
</template>

<script>
export default {
    props: {
        entries: {
            type: Array,
            required: true
        },
    },
    computed: {
        testCaseText (entry) {
            if (!entry.testcase) return "No test"
            text = "Q" + entry.testcase.quality + "\n" + entry.testcase.size
            if (entry.testcase.isBinary) text += "\n    (binary)"
            return text
        },
        staticLogo (name) {
            return window.location.origin + "/static/img/os/" + name + ".png"
        }
    }
}
</script>

<style scoped>
</style>