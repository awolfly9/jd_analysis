/**
 * Created by lgq on 17/5/3.
 */

function switchemail() {
    var text = document.getElementById('email');
    if (text.style.display === 'none') {
        text.style.display = 'inline';
        // text.style.color = '#FFFFFF';
    }
    else {
        text.style.display = 'none';
    }
}