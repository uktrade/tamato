const nodeListForEach = (nodes, callback) => {
    if (window.NodeList.prototype.forEach) {
        return nodes.forEach(callback)
    }
    for (let i = 0; i < nodes.length; i++) {
        callback.call(window, nodes[i], i, nodes)
    }
}

const newLine = /[\n\r]/g;
const removeNewLine = (str) => str.replace(newLine, "")

const cleanResults = (results) => {
    /*
    Results which contain new line characters are considered as a new query when
    selected, causing results to be repopulated unnecessarily. To prevent this,
    we can remove new line characters from results since they're unimportant here.
    */
    for (let i = 0, len = results.length; i < len; i++) {
        results[i].label = removeNewLine(results[i].label);
    }
    return results
}

export { nodeListForEach, removeNewLine, cleanResults }
