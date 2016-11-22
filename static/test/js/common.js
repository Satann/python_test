// 判断值undefined
var check_undefined = function(obj) {
	if (obj == undefined) {
		return "";
	} else {
		return obj;
	}
};

// 时间格式处理
var date_convert = function(longTime) {
	var date = new Date(parseInt(longTime));
	return date.format("yyyy-MM-dd hh:mm:ss");
};

var string_convert = function(dateStr) {
	dateStr = dateStr.replace(/-/g, "/");
	var date = new Date(dateStr);
	return date;
};

//排序array
function getSortFun(order, sortBy) {
    var ordAlpah = (order == 'asc') ? '>' : '<';
    var sortFun = new Function('a', 'b', 'return a.' + sortBy + ordAlpah + 'b.' + sortBy + '?1:-1');
    return sortFun;
}


Date.prototype.format = function(format) {
	var o = {
		"M+" : this.getMonth() + 1, // month
		"d+" : this.getDate(), // day
		"h+" : this.getHours(), // hour
		"m+" : this.getMinutes(), // minute
		"s+" : this.getSeconds(), // seconds
		"q+" : Math.floor((this.getMonth() + 3) / 3), // quarter
		"S" : this.getMilliseconds()
	// millisecond
	};
	if (/(y+)/.test(format))
		format = format.replace(RegExp.$1, (this.getFullYear() + "")
				.substr(4 - RegExp.$1.length));
	for ( var k in o)
		if (new RegExp("(" + k + ")").test(format))
			format = format.replace(RegExp.$1, RegExp.$1.length == 1 ? o[k]
					: ("00" + o[k]).substr(("" + o[k]).length));
	return format;
};

/**
 * 请求参数中加时间戳
 */
function noCacheUrl(_url) {
	if (_url.indexOf("?") > 0) {
		return _url + "&_time=" + new Date().getTime();
	}
	return _url + "?_time=" + new Date().getTime();
}


