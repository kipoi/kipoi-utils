import pytest
from kipoi_utils.external.torchvision.dataset_utils import download_url

def test_download_url_valid_link(tmp_path, capfd):
    download_url("https://zenodo.org/record/1466088/files/example_files-hg19.chr22.fa?download=1", tmp_path, 
                    'downloaded.fa', '936544855b253835442a0f253dd4b083')
    out, err = capfd.readouterr()
    for second in ['0.1', '0.2', '0.4', '0.8', '1.6', '3.2']:
        assert "Waiting " + second + " seconds before retrying" not in out

    assert (tmp_path / 'downloaded.fa').exists()
    
def test_download_url_retry(tmp_path, capfd):
    with pytest.raises(Exception) as exc_info:
        download_url("http://invalid.url", tmp_path, 'downloaded.h5')
    out, err = capfd.readouterr()
    for second in ['0.1', '0.2', '0.4', '0.8', '1.6', '3.2']:
        assert "Waiting " + second + " seconds before retrying" in out
    output = str(exc_info.value)
    assert 'Can not download http://invalid.url' in output
    error_msgs = ['Name or service not known', 'nodename nor servname provided, or not known']
    assert any(msg in output for msg in error_msgs)