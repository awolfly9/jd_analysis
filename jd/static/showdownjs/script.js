/**
 * Created by lgq on 17/2/27.
 */


function run() {
    var text = document.getElementById('sourceTA').value,
        target = document.getElementById('targetDiv'),
        converter = new showdown.Converter({
            'omitExtraWLInCodeBlocks': 'true',
            'parseImgDimensions': 'true',
            'noHeaderId': 'false',
            // 'prefixHeaderId': 'true',
            'simplifiedAutoLink': 'true',
            'literalMidWordUnderscores': 'true',
            'strikethrough': 'true',
            'tables': 'true',
            'tablesHeaderId': 'true',
            'ghCodeBlocks': 'true',
            'tasklists': 'true',
            'smoothLivePreview': 'true',
            'prefixHeaderId': 'false',
            'disableForced4SpacesIndentedSublists': 'true',
            'ghCompatibleHeaderId': 'true',
            'smartIndentationFix': 'false',
            'excludeTrailingPunctuationFromURLs': 'false',
            'simpleLineBreaks': 'false',
            'requireSpaceBeforeHeadingText': 'false',
            'ghMentions': 'false'
        }),

        html = converter.makeHtml(text);

    target.innerHTML = html;
}