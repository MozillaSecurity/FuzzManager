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
        <tr v-for="(entry, index) in entries" :key="entry.id" :class="{'odd': index % 2 === 0, 'even': index % 2 !== 0}">
            <td>
                <a :href="entry.url">{{ entry.id }}</a>
            </td>
            <!-- TODO: Restore date formatting (previously: `entry.created|date:"r"`) -->
            <td>{{ entry.created }}</td>
            <td>{{ entry.shortSignature }}</td>
            <td>{{ entry.crashAddress }}</td>
            <td>{{ testCaseText(entry) }}</td>
            <td>{{ entry.product }}</td>
            <td>{{ entry.product_version }}</td>
            <td>{{ entry.platform }}</td>
            <td>
                <img width="16px" height="16px" alt="Linux" :src="staticLogo(entry.os)" v-if="entry.os == 'linux'"/>
                <img width="16px" height="16px" alt="MacOS" :src="staticLogo(entry.os)" v-else-if="entry.os == 'macosx'"/>
                <img width="16px" height="16px" alt="Windows" :src="staticLogo(entry.os)" v-else-if="entry.os == 'windows'"/>
                <img width="16px" height="16px" alt="Android" :src="staticLogo(entry.os)" v-else-if="entry.os == 'android'"/>
                <template v-else>{{ entry.os }}</template>
            </td>
            <td>{{ entry.tool }}</td>
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
    methods: {
        testCaseText (entry) {
            if (!entry.testcase) return "No test"
            let text = "Q" + entry.testcase_quality + "\n" + entry.testcase_size
            if (entry.testcase_isBinary) text += "\n    (binary)"
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